import { useNavigate } from "react-router-dom";

interface CalendarViewSwitcherProps {
  active: "month" | "week" | "year";
  monthHref: string;
  weekHref: string;
  yearHref: string;
}

export function CalendarViewSwitcher({
  active,
  monthHref,
  weekHref,
  yearHref,
}: CalendarViewSwitcherProps) {
  const navigate = useNavigate();

  function btnClass(view: CalendarViewSwitcherProps["active"]): string {
    return view === active ? "zoom-control__btn zoom-control__btn--active" : "zoom-control__btn";
  }

  return (
    <div className="zoom-control">
      <button type="button" className={btnClass("week")} onClick={() => navigate(weekHref)}>
        Week
      </button>
      <button type="button" className={btnClass("month")} onClick={() => navigate(monthHref)}>
        Month
      </button>
      <button type="button" className={btnClass("year")} onClick={() => navigate(yearHref)}>
        Year
      </button>
    </div>
  );
}
