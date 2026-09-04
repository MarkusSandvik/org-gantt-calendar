import { monthBlocks, weekBlocks, type ZoomLevel } from "./dateScale";

interface TimelineHeaderProps {
  rangeStart: Date;
  rangeEnd: Date;
  zoom: ZoomLevel;
  labelWidth: number;
}

export function TimelineHeader({ rangeStart, rangeEnd, zoom, labelWidth }: TimelineHeaderProps) {
  const months = monthBlocks(rangeStart, rangeEnd, zoom);
  const showWeeks = zoom === "week" || zoom === "month";
  const weeks = showWeeks ? weekBlocks(rangeStart, rangeEnd, zoom) : [];

  return (
    <div className="gantt-header">
      <div className="gantt-header__corner" style={{ width: labelWidth }}>
        Activity
      </div>
      <div className="gantt-header__timeline">
        <div className="gantt-header__row gantt-header__row--month">
          {months.map((m) => (
            <div key={m.key} className="gantt-header__cell" style={{ left: m.x, width: m.width }}>
              {m.label}
            </div>
          ))}
        </div>
        {showWeeks && (
          <div className="gantt-header__row gantt-header__row--week">
            {weeks.map((w) => (
              <div
                key={w.key}
                className="gantt-header__cell gantt-header__cell--week"
                style={{ left: w.x, width: w.width }}
              >
                {w.label}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
