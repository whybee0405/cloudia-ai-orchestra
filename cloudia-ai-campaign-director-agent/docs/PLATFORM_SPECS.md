# Platform Specifications

All specs are enforced by `PLATFORM_SPECS` in `backend/config.py`.  
The FormatterAgent reads these at runtime. Character limits are validated by CopywriterAgent.

---

## Instagram

| Content Type | Width | Height | Format | Max Size |
|-------------|-------|--------|--------|---------|
| image_post | 1080 | 1080 | JPG | 8 MB |
| portrait | 1080 | 1350 | JPG | 8 MB |
| landscape | 1080 | 566 | JPG | 8 MB |
| story | 1080 | 1920 | JPG | 30 MB |
| reel | 1080 | 1920 | MP4 | 650 MB |
| carousel | 1080 | 1080 | JPG | 10 slides max |

- Caption max: **2,200 characters**
- Hashtag max: **30**
- Reel duration: **3–90 seconds**

---

## Facebook

| Content Type | Width | Height | Format | Max Size |
|-------------|-------|--------|--------|---------|
| image_post | 1200 | 630 | JPG | 8 MB |
| story | 1080 | 1920 | JPG | 30 MB |
| reel | 1080 | 1920 | MP4 | 1,000 MB |
| video | 1280 | 720 | MP4 | 10,240 MB |

- Caption max: **63,206 characters**
- Reel duration: up to 90 seconds
- Video duration: up to 4 hours

---

## TikTok

| Content Type | Width | Height | Format | Max Size |
|-------------|-------|--------|--------|---------|
| video | 1080 | 1920 | MP4 | 287 MB |

- Caption max: **2,200 characters**
- Hashtag max: **5**
- Duration: **3–600 seconds**

---

## LinkedIn

| Content Type | Width | Height | Format | Max Size |
|-------------|-------|--------|--------|---------|
| image_post | 1200 | 627 | JPG | 5 MB |
| video | 1920 | 1080 | MP4 | 5,120 MB |

- Caption max: **3,000 characters**
- Video duration: up to 10 minutes

---

## Twitter / X

| Content Type | Width | Height | Format | Max Size |
|-------------|-------|--------|--------|---------|
| image_post | 1600 | 900 | JPG | 5 MB |
| video | 1280 | 720 | MP4 | 512 MB |

- Caption max: **280 characters**
- Video duration: up to 140 seconds

---

## YouTube

| Content Type | Width | Height | Format | Max Size |
|-------------|-------|--------|--------|---------|
| video | 1920 | 1080 | MP4 | 256,000 MB |
| short | 1080 | 1920 | MP4 | 256,000 MB |
| thumbnail | 1280 | 720 | JPG | 2 MB |

- Description max: **5,000 characters**
- Short duration: up to 60 seconds

---

## Google Business

| Content Type | Width | Height | Format | Max Size |
|-------------|-------|--------|--------|---------|
| image_post | 720 | 540 | JPG | 5 MB |

- Min dimensions: 400 × 300
- Caption max: **1,500 characters**

---

## WhatsApp

| Content Type | Format | Max Size |
|-------------|--------|---------|
| image | JPG | 5 MB |
| video | MP4 | 64 MB |

- Message max: **4,096 characters**
- Video duration: up to 90 seconds

---

## Optimal Posting Windows (SAST)

Defined in `backend/agents/publishing/scheduler.py`:

| Platform | Windows |
|---------|---------|
| Instagram | 08:00–09:00, 19:00–21:00 |
| Facebook | 10:00–15:00 |
| TikTok | 07:00–09:00, 19:00–23:00 |
| LinkedIn | 08:00–10:00 |
| WhatsApp | 09:00–11:00 |
| Google Business | 10:00–12:00 |
| YouTube | 15:00–18:00 |
| Twitter | 09:00–10:00, 12:00–13:00, 17:00–18:00 |

All times in **SAST (Africa/Johannesburg, UTC+2)**, stored as **UTC** in the database.
