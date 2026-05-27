import { useCallback } from 'react';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale/en-US';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import PlatformBadge from './PlatformBadge';

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: () => startOfWeek(new Date(), { weekStartsOn: 0 }),
  getDay,
  locales: { 'en-US': enUS },
});

const CONTENT_TYPE_COLORS = {
  image: '#3b82f6',
  video: '#8b5cf6',
  text: '#10b981',
  carousel: '#f59e0b',
  reel: '#ec4899',
  story: '#6366f1',
};

function EventRenderer({ event }) {
  const color = CONTENT_TYPE_COLORS[event.resource?.content_type] || '#6b7280';
  return (
    <div
      className="flex items-center gap-1 px-1 py-0.5 rounded text-white text-xs truncate"
      style={{ backgroundColor: color }}
    >
      <span className="truncate">{event.title}</span>
      {event.resource?.platform && (
        <span className="opacity-80 shrink-0 text-xs">
          {event.resource.platform.slice(0, 2).toUpperCase()}
        </span>
      )}
    </div>
  );
}

export default function CalendarView({ events = [], onSelectEvent, onEventDrop, onNavigate, date }) {
  const calendarEvents = events.map((item) => ({
    id: item.id,
    title: item.title || item.asset?.title || `Post #${item.id}`,
    start: new Date(item.scheduled_at || item.start),
    end: new Date(item.scheduled_at || item.start),
    allDay: false,
    resource: item,
  }));

  const handleEventDrop = useCallback(
    ({ event, start }) => {
      onEventDrop && onEventDrop(event.resource, start);
    },
    [onEventDrop]
  );

  return (
    <div className="h-full min-h-[600px]">
      <Calendar
        localizer={localizer}
        events={calendarEvents}
        startAccessor="start"
        endAccessor="end"
        style={{ height: '100%' }}
        onSelectEvent={(event) => onSelectEvent && onSelectEvent(event.resource)}
        onNavigate={onNavigate}
        date={date}
        views={['month', 'week', 'day']}
        defaultView="month"
        components={{
          event: EventRenderer,
        }}
        popup
        draggableAccessor={() => !!onEventDrop}
      />
    </div>
  );
}
