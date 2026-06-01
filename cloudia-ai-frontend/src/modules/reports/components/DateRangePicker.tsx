interface DateRangePickerProps {
  dateFrom: string
  dateTo: string
  onFromChange: (v: string) => void
  onToChange: (v: string) => void
}

export function DateRangePicker({ dateFrom, dateTo, onFromChange, onToChange }: DateRangePickerProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-500 whitespace-nowrap">From</label>
        <input
          type="date"
          value={dateFrom}
          onChange={e => onFromChange(e.target.value)}
          className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-400"
        />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-500 whitespace-nowrap">To</label>
        <input
          type="date"
          value={dateTo}
          onChange={e => onToChange(e.target.value)}
          className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-400"
        />
      </div>
    </div>
  )
}
