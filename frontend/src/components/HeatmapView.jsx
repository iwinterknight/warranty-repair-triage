import { ResponsiveHeatMap } from "@nivo/heatmap";

// 2-actor view: rows = first group field, columns = second, cell colour = measure (priority score).
// This is the "where's the concentration" gestalt; the table is the precise readout.
export default function HeatmapView({ result, gRow, gCol, onCell }) {
  const rows = result?.rows || [];
  const rowKeys = [...new Set(rows.map((r) => String(r[gRow])))];
  const colKeys = [...new Set(rows.map((r) => String(r[gCol])))];

  const data = rowKeys.map((rk) => ({
    id: rk,
    data: colKeys.map((ck) => {
      const cell = rows.find((r) => String(r[gRow]) === rk && String(r[gCol]) === ck);
      return { x: ck, y: cell ? Number(Number(cell.measure).toFixed(1)) : null };
    }),
  }));

  if (!rows.length) return <p className="muted">No rows for this query.</p>;

  return (
    <div style={{ height: Math.max(260, rowKeys.length * 34 + 120) }}>
      <ResponsiveHeatMap
        data={data}
        margin={{ top: 70, right: 60, bottom: 30, left: 150 }}
        axisTop={{ tickRotation: -35 }}
        axisLeft={{ legend: gRow, legendPosition: "middle", legendOffset: -130 }}
        colors={{ type: "sequential", scheme: "blues" }}
        emptyColor="#f4f6f8"
        borderWidth={1}
        borderColor="#dfe3e8"
        valueFormat=">-.1f"
        labelTextColor={{ from: "color", modifiers: [["darker", 2.2]] }}
        hoverTarget="cell"
        animate={false}
        onClick={(cell) => onCell && onCell(String(cell.serieId), String(cell.data.x))}
      />
    </div>
  );
}
