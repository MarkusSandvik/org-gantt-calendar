import type { Dependency } from "../../api/types";
import { ROW_HEIGHT, type RowPosition } from "./rowLayout";

interface DependencyArrowsProps {
  dependencies: Dependency[];
  positions: Map<string, RowPosition>;
  labelWidth: number;
  width: number;
  height: number;
}

/** Simple three-segment elbow connector: out from the predecessor's end,
 * across, then into the successor's start. When the successor doesn't sit
 * comfortably to the right of the predecessor (unusual, but possible with
 * negative-looking layouts), it routes a short loop out and back instead of
 * drawing back through the predecessor's own bar. */
function buildPath(x2: number, y2: number, x1: number, y1: number): string {
  if (x1 > x2 + 12) {
    const mid = x2 + (x1 - x2) / 2;
    return `M ${x2} ${y2} H ${mid} V ${y1} H ${x1}`;
  }
  const out = x2 + 16;
  return `M ${x2} ${y2} H ${out} V ${y1} H ${x1}`;
}

export function DependencyArrows({
  dependencies,
  positions,
  labelWidth,
  width,
  height,
}: DependencyArrowsProps) {
  return (
    <svg className="gantt-dependency-layer" width={width} height={height}>
      <defs>
        <marker
          id="gantt-arrowhead"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M0,0 L10,5 L0,10 z" fill="#8a93a1" />
        </marker>
      </defs>
      {dependencies.map((dep) => {
        const pred = positions.get(`${dep.predecessor_type}-${dep.predecessor_id}`);
        const succ = positions.get(`${dep.successor_type}-${dep.successor_id}`);
        if (!pred || !succ) return null;
        const x2 = labelWidth + pred.endX;
        const y2 = pred.y + ROW_HEIGHT / 2;
        const x1 = labelWidth + succ.startX;
        const y1 = succ.y + ROW_HEIGHT / 2;
        return (
          <path
            key={dep.id}
            d={buildPath(x2, y2, x1, y1)}
            className="gantt-dependency-arrow"
            markerEnd="url(#gantt-arrowhead)"
          >
            <title>
              {dep.predecessor_label} → {dep.successor_label}
              {dep.lag_days ? ` (+${dep.lag_days}d lag)` : ""}
            </title>
          </path>
        );
      })}
    </svg>
  );
}
