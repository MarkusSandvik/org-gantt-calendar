import { useNavigate } from "react-router-dom";

interface CalendarViewSwitcherProps {
  active: "month" | "week" | "year" | "wheel";
  monthHref: string;
  weekHref: string;
  yearHref: string;
  wheelHref: string;
}

export function CalendarViewSwitcher({
  active,
  monthHref,
  weekHref,
  yearHref,
  wheelHref,
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
      <button type="button" className={btnClass("wheel")} onClick={() => navigate(wheelHref)}>
        Wheel
      </button>
    </div>
  );
}
