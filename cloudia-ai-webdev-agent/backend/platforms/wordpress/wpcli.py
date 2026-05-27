"""
WP-CLI command runner for the CloudIA agent system.

Executes WP-CLI commands either via SSH on a remote server or via local subprocess.
SSH is optional — if no SSH host is configured, or the connection test fails,
all commands return ``None`` gracefully with a warning log and no exception.

Typical usage:
    cli = WPCLIClient(ssh_host="1.2.3.4", ssh_user="ubuntu",
                      ssh_key_path="/home/ubuntu/.ssh/id_rsa",
                      wp_path="/var/www/html")
    cli.install_theme("astra")
    cli.install_plugin("yoast-seo")
    cli.update_permalinks()
"""

from __future__ import annotations

import subprocess
import shlex
from typing import Optional

import structlog

log = structlog.get_logger()


class WPCLIError(Exception):
    """Raised when a WP-CLI command exits with a non-zero status code."""


class WPCLIClient:
    """WP-CLI command runner via SSH or local subprocess.

    SSH is optional — if SSH connection fails, all methods return gracefully
    with a warning log and no exception raised to the caller.
    """

    def __init__(
        self,
        ssh_host: Optional[str] = None,
        ssh_user: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        wp_path: str = "/var/www/html",
    ) -> None:
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_key_path = ssh_key_path
        self.wp_path = wp_path
        self.ssh_available = self._test_connection()

    # ------------------------------------------------------------------
    # Connection testing
    # ------------------------------------------------------------------

    def _test_connection(self) -> bool:
        """Test SSH connection. Returns False if SSH not configured or unreachable."""
        if not self.ssh_host:
            log.info("wpcli_ssh_not_configured", reason="no ssh_host provided")
            return False

        cmd = self._build_ssh_command("echo ping")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and "ping" in result.stdout:
                log.info("wpcli_ssh_connected", host=self.ssh_host)
                return True
            log.warning(
                "wpcli_ssh_failed",
                host=self.ssh_host,
                returncode=result.returncode,
                stderr=result.stderr[:200],
            )
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log.warning("wpcli_ssh_unreachable", host=self.ssh_host, error=str(exc))
            return False

    def _build_ssh_command(self, remote_command: str) -> list[str]:
        """Build an SSH command list for subprocess."""
        cmd: list[str] = ["ssh"]
        if self.ssh_key_path:
            cmd += ["-i", self.ssh_key_path]
        # Strict host key checking disabled for automated use
        cmd += [
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
        ]
        if self.ssh_user:
            cmd.append(f"{self.ssh_user}@{self.ssh_host}")
        else:
            cmd.append(self.ssh_host)
        cmd.append(remote_command)
        return cmd

    # ------------------------------------------------------------------
    # Command runner
    # ------------------------------------------------------------------

    def _run(self, wp_command: str) -> Optional[str]:
        """Run a WP-CLI command. Returns stdout string or None if SSH unavailable.

        The full shell command sent to the remote host is:
            wp --path=/var/www/html <wp_command> --allow-root
        """
        if not self.ssh_available:
            log.warning("wpcli_skipped", reason="SSH not available", command=wp_command)
            return None

        # Build the WP-CLI command to run on the remote host
        full_wp_cmd = (
            f"wp --path={shlex.quote(self.wp_path)} {wp_command} --allow-root"
        )
        ssh_cmd = self._build_ssh_command(full_wp_cmd)

        log.debug("wpcli_run", command=full_wp_cmd, host=self.ssh_host)
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            log.error("wpcli_timeout", command=wp_command)
            raise WPCLIError(f"WP-CLI command timed out: {wp_command}")
        except (FileNotFoundError, OSError) as exc:
            log.error("wpcli_exec_error", command=wp_command, error=str(exc))
            raise WPCLIError(f"Could not execute SSH command: {exc}") from exc

        if result.returncode != 0:
            log.error(
                "wpcli_command_failed",
                command=wp_command,
                returncode=result.returncode,
                stderr=result.stderr[:500],
            )
            raise WPCLIError(
                f"WP-CLI command failed (exit {result.returncode}): "
                f"{result.stderr[:300] or result.stdout[:300]}"
            )

        output = result.stdout.strip()
        log.debug("wpcli_output", command=wp_command, output=output[:200])
        return output

    # ------------------------------------------------------------------
    # Public commands
    # ------------------------------------------------------------------

    def install_theme(self, theme_slug: str, activate: bool = True) -> bool:
        """Download and optionally activate a theme from the WP.org repository.

        Returns True on success, False if SSH is unavailable.
        """
        cmd = f"theme install {shlex.quote(theme_slug)}"
        if activate:
            cmd += " --activate"
        try:
            self._run(cmd)
            log.info("wpcli_theme_installed", theme=theme_slug, activated=activate)
            return True
        except WPCLIError:
            log.error("wpcli_theme_install_failed", theme=theme_slug)
            raise

    def install_plugin(self, plugin_slug: str, activate: bool = True) -> bool:
        """Download and optionally activate a plugin from the WP.org repository.

        Returns True on success, False if SSH is unavailable.
        """
        cmd = f"plugin install {shlex.quote(plugin_slug)}"
        if activate:
            cmd += " --activate"
        try:
            self._run(cmd)
            log.info("wpcli_plugin_installed", plugin=plugin_slug, activated=activate)
            return True
        except WPCLIError:
            log.error("wpcli_plugin_install_failed", plugin=plugin_slug)
            raise

    def update_permalinks(self, structure: str = "/%postname%/") -> bool:
        """Flush rewrite rules and set the permalink structure.

        Returns True on success, False if SSH is unavailable.
        """
        if not self.ssh_available:
            log.warning("wpcli_skipped", reason="SSH not available", command="rewrite flush")
            return False

        try:
            # Update option first, then flush
            self.set_option("permalink_structure", structure)
            self._run("rewrite flush --hard")
            log.info("wpcli_permalinks_updated", structure=structure)
            return True
        except WPCLIError:
            log.error("wpcli_permalinks_failed", structure=structure)
            raise

    def clear_cache(self) -> bool:
        """Flush the WordPress object cache.

        Returns True on success, False if SSH is unavailable.
        """
        if not self.ssh_available:
            log.warning("wpcli_skipped", reason="SSH not available", command="cache flush")
            return False

        try:
            self._run("cache flush")
            log.info("wpcli_cache_cleared")
            return True
        except WPCLIError:
            # Cache flush failure is non-fatal
            log.warning("wpcli_cache_flush_failed")
            return False

    def set_option(self, option_name: str, value: str) -> bool:
        """Set a WordPress option via wp option update.

        Returns True on success, False if SSH is unavailable.
        """
        if not self.ssh_available:
            log.warning(
                "wpcli_skipped",
                reason="SSH not available",
                command=f"option update {option_name}",
            )
            return False

        cmd = f"option update {shlex.quote(option_name)} {shlex.quote(value)}"
        try:
            self._run(cmd)
            log.info("wpcli_option_set", option=option_name)
            return True
        except WPCLIError:
            log.error("wpcli_option_set_failed", option=option_name)
            raise
