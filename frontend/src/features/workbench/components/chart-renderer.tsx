"use client";

import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartSpec } from "@/types/displays";

const COLORS = ["#176b87", "#3c9a79", "#d1873b", "#8064b5", "#cc5b63"];
const SWITCHABLE_TYPES = ["line", "area", "bar"] as const;
type SwitchableType = (typeof SWITCHABLE_TYPES)[number];
type LabelPolicy = {
  isTime: boolean;
  includeYear: boolean;
  limit: number;
  rotate: boolean;
  horizontalBars: boolean;
  interval: number;
};
type RenderSeries = { field: string; label: string; color: string };
type PreparedChart = { data: ChartSpec["data"]; series: RenderSeries[] };

const label = (spec: ChartSpec, field: string, index: number) =>
  spec.series.find((series) => series.field === field)?.label ?? field ?? `Series ${index + 1}`;
const supportsSwitching = (
  type: ChartSpec["type"],
): type is "line" | "area" | "bar" | "stacked_bar" =>
  ["line", "area", "bar", "stacked_bar"].includes(type);

function compactDate(value: unknown, includeYear = false) {
  const match = /^(\d{4})-(\d{2})(?:-\d{2})?$/.exec(String(value));
  if (!match) return String(value);
  const month = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ][Number(match[2]) - 1];
  return includeYear ? `${month} ’${match[1].slice(2)}` : month;
}
function truncateLabel(value: unknown, limit: number) {
  const text = String(value);
  return text.length <= limit ? text : `${text.slice(0, Math.max(limit - 1, 1)).trimEnd()}…`;
}
export function xAxisLabelPolicy(
  data: ChartSpec["data"],
  xField: string,
  chartType: ChartSpec["type"],
): LabelPolicy {
  const labels = data.map((row) => String(row[xField] ?? ""));
  const isTime = labels.length > 0 && labels.every((value) => /^\d{4}-\d{2}(-\d{2})?$/.test(value));
  const longest = Math.max(0, ...labels.map((value) => value.length));
  // Preserve a maximum of eight time ticks. `interval={0}` renders every label
  // and is unreadable for long timelines or unpivoted comparison datasets.
  if (isTime)
    return {
      isTime: true,
      includeYear: new Set(labels.map((value) => value.slice(0, 4))).size > 1,
      limit: 10,
      rotate: false,
      horizontalBars: false,
      interval: Math.max(0, Math.ceil(labels.length / 8) - 1),
    };
  // Category-label rule: short labels stay intact; medium labels are angled and
  // abbreviated; long or dense bar categories become horizontal bars. Full names
  // always remain available in the hover tooltip and source-data table.
  if (longest <= 12 && labels.length <= 8)
    return {
      isTime: false,
      includeYear: false,
      limit: 12,
      rotate: false,
      horizontalBars: false,
      interval: 0,
    };
  if (longest <= 20 && labels.length <= 10)
    return {
      isTime: false,
      includeYear: false,
      limit: 16,
      rotate: true,
      horizontalBars: false,
      interval: Math.max(0, Math.ceil(labels.length / 8) - 1),
    };
  return {
    isTime: false,
    includeYear: false,
    limit: 18,
    rotate: true,
    horizontalBars: chartType === "bar" || chartType === "stacked_bar",
    interval: Math.max(0, Math.ceil(labels.length / 8) - 1),
  };
}

export function prepareChart(chart: ChartSpec): PreparedChart {
  const ordinarySeries = chart.y_fields.map((field, index) => ({
    field,
    label: label(chart, field, index),
    color: COLORS[index % COLORS.length],
  }));
  if (
    !chart.x_field ||
    chart.y_fields.length !== 1 ||
    !["line", "area", "bar", "stacked_bar"].includes(chart.type)
  )
    return { data: chart.data, series: ordinarySeries };
  const valueField = chart.y_fields[0];
  const columns = Object.keys(chart.data[0] ?? {}).filter(
    (field) => field !== chart.x_field && field !== valueField,
  );
  const categoryField = columns.find((field) => {
    const values = new Set(
      chart.data
        .map((row) => row[field])
        .filter((value): value is string => typeof value === "string"),
    );
    const xValues = new Set(chart.data.map((row) => row[chart.x_field!]));
    return values.size >= 2 && values.size <= 8 && chart.data.length > xValues.size;
  });
  if (!categoryField) return { data: chart.data, series: ordinarySeries };
  const categories = [
    ...new Set(
      chart.data
        .map((row) => row[categoryField])
        .filter((value): value is string => typeof value === "string"),
    ),
  ];
  const fields = new Map(
    categories.map((category, index) => [category, `${valueField}__series_${index}`]),
  );
  const rows = new Map<string, ChartSpec["data"][number]>();
  for (const row of chart.data) {
    const xValue = row[chart.x_field];
    const category = row[categoryField];
    if (xValue === undefined || typeof category !== "string") continue;
    const key = String(xValue);
    const target = rows.get(key) ?? ({ [chart.x_field]: xValue } as ChartSpec["data"][number]);
    target[fields.get(category)!] = row[valueField];
    rows.set(key, target);
  }
  return {
    data: [...rows.values()],
    series: categories.map((category, index) => ({
      field: fields.get(category)!,
      label: category,
      color: COLORS[index % COLORS.length],
    })),
  };
}
function formatValue(value: unknown, chart: ChartSpec) {
  if (typeof value !== "number") return String(value);
  const rendered = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: chart.formatting?.decimal_places ?? 0,
    notation: Math.abs(value) >= 1_000_000 ? "compact" : "standard",
  }).format(value);
  return chart.formatting?.currency ? `${chart.formatting.currency}${rendered}` : rendered;
}

export function ChartRenderer({
  chart,
  onExplore,
}: {
  chart: ChartSpec;
  /** Offered by the transcript; omitted inside the panel so it cannot recurse. */
  onExplore?: () => void;
}) {
  const initialType: SwitchableType =
    chart.type === "area"
      ? "area"
      : chart.type === "bar" || chart.type === "stacked_bar"
        ? "bar"
        : "line";
  const [visualType, setVisualType] = useState<SwitchableType>(initialType);
  const [showData, setShowData] = useState(false);
  if (chart.type === "kpi")
    return (
      <div className="kpi-row">
        {chart.kpis.map((kpi) => (
          <article className="kpi-card" key={kpi.label}>
            <span>{kpi.label}</span>
            <strong>{kpi.value}</strong>
            {kpi.change && <small>{kpi.change}</small>}
          </article>
        ))}
      </div>
    );
  if (!chart.data.length) return <div className="display-empty">No chart data is available.</div>;
  if (chart.type === "table") return <DataTable chart={chart} onExplore={onExplore} />;
  if (!chart.x_field || !chart.y_fields.length)
    return <div className="display-empty">This chart specification is incomplete.</div>;

  const renderType = supportsSwitching(chart.type) ? visualType : chart.type;
  const prepared = prepareChart(chart);
  const series = prepared.series;
  const labels = xAxisLabelPolicy(prepared.data, chart.x_field, renderType);
  const formatXAxis = (value: unknown) =>
    labels.isTime ? compactDate(value, labels.includeYear) : truncateLabel(value, labels.limit);
  const common = (
    <>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis
        dataKey={chart.x_field}
        tickFormatter={formatXAxis}
        interval={labels.interval}
        minTickGap={8}
        angle={labels.rotate ? -30 : 0}
        textAnchor={labels.rotate ? "end" : "middle"}
        height={labels.rotate ? 58 : 30}
      />
      <YAxis width={100} tickFormatter={(value) => formatValue(value, chart)} />
      <Tooltip
        formatter={(value) => formatValue(value, chart)}
        labelFormatter={(value) => String(value)}
      />
      {chart.formatting?.show_legend !== false && <Legend />}
    </>
  );
  const horizontalBarCommon = (
    <>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis type="number" tickFormatter={(value) => formatValue(value, chart)} />
      <YAxis
        type="category"
        dataKey={chart.x_field}
        width={150}
        tickFormatter={(value) => truncateLabel(value, 22)}
      />
      <Tooltip
        formatter={(value) => formatValue(value, chart)}
        labelFormatter={(value) => String(value)}
      />
      {chart.formatting?.show_legend !== false && <Legend />}
    </>
  );
  let body;
  if (renderType === "line")
    body = (
      <LineChart data={prepared.data} margin={{ top: 8, right: 18, bottom: 8, left: 8 }}>
        {common}
        {series.map((item) => (
          <Line
            key={item.field}
            type="monotone"
            dataKey={item.field}
            name={item.label}
            stroke={item.color}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    );
  else if (renderType === "area")
    body = (
      <AreaChart data={prepared.data} margin={{ top: 8, right: 18, bottom: 8, left: 8 }}>
        {common}
        {series.map((item) => (
          <Area
            key={item.field}
            type="monotone"
            dataKey={item.field}
            name={item.label}
            stroke={item.color}
            fill={item.color}
            fillOpacity={0.2}
          />
        ))}
      </AreaChart>
    );
  else if (renderType === "pie")
    body = (
      <PieChart>
        <Tooltip formatter={(value) => formatValue(value, chart)} />
        <Legend />
        <Pie data={chart.data} dataKey={chart.y_fields[0]} nameKey={chart.x_field} outerRadius={92}>
          {chart.data.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
      </PieChart>
    );
  else if (renderType === "scatter")
    body = (
      <ScatterChart margin={{ top: 8, right: 18, bottom: 8, left: 8 }}>
        {common}
        <Scatter data={chart.data} fill={COLORS[0]} />
      </ScatterChart>
    );
  else if (labels.horizontalBars)
    body = (
      <BarChart
        data={prepared.data}
        layout="vertical"
        margin={{ top: 8, right: 18, bottom: 8, left: 8 }}
      >
        {horizontalBarCommon}
        {series.map((item) => (
          <Bar
            key={item.field}
            dataKey={item.field}
            name={item.label}
            fill={item.color}
            stackId={chart.type === "stacked_bar" ? "stack" : undefined}
            radius={[0, 3, 3, 0]}
          />
        ))}
      </BarChart>
    );
  else
    body = (
      <BarChart data={prepared.data} margin={{ top: 8, right: 18, bottom: 8, left: 8 }}>
        {common}
        {series.map((item) => (
          <Bar
            key={item.field}
            dataKey={item.field}
            name={item.label}
            fill={item.color}
            stackId={chart.type === "stacked_bar" ? "stack" : undefined}
            radius={[3, 3, 0, 0]}
          />
        ))}
      </BarChart>
    );

  return (
    <section className="analytical-display">
      <header>
        <div>
          <h3>{chart.title}</h3>
          {chart.description && <p>{chart.description}</p>}
          <small>Based on {chart.source_query_ids.join(", ")}</small>
        </div>
        <div className="display-actions">
          {onExplore && (
            <button type="button" className="explore-display" onClick={onExplore}>
              Explore
            </button>
          )}
          <span className="interactive-badge">Interactive</span>
        </div>
      </header>
      {supportsSwitching(chart.type) && (
        <div className="chart-controls" aria-label="Chart display options">
          {SWITCHABLE_TYPES.map((type) => (
            <button
              key={type}
              type="button"
              className={visualType === type ? "active" : ""}
              aria-pressed={visualType === type}
              onClick={() => setVisualType(type)}
            >
              {type === "line" ? "Line" : type === "area" ? "Area" : "Bar"}
            </button>
          ))}
          <button
            type="button"
            aria-pressed={showData}
            className={showData ? "active" : ""}
            onClick={() => setShowData((current) => !current)}
          >
            {showData ? "Hide data" : "Show data"}
          </button>
        </div>
      )}
      <div className="chart-canvas">
        <ResponsiveContainer width="100%" height={310}>
          {body}
        </ResponsiveContainer>
      </div>
      {showData && <DataTable chart={chart} embedded />}
      <CsvDownload chart={chart} />
    </section>
  );
}

function DataTable({
  chart,
  embedded = false,
  onExplore,
}: {
  chart: ChartSpec;
  embedded?: boolean;
  onExplore?: () => void;
}) {
  const columns = Object.keys(chart.data[0] ?? {});
  const content = (
    <div className="data-table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {chart.data.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{formatValue(row[column], chart)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  return embedded ? (
    content
  ) : (
    <section className="analytical-display">
      <header>
        <div>
          <h3>{chart.title}</h3>
          <small>Based on {chart.source_query_ids.join(", ")}</small>
        </div>
        {onExplore && (
          <div className="display-actions">
            <button type="button" className="explore-display" onClick={onExplore}>
              Explore
            </button>
          </div>
        )}
      </header>
      {content}
      <CsvDownload chart={chart} />
    </section>
  );
}
function CsvDownload({ chart }: { chart: ChartSpec }) {
  const download = () => {
    const fields = Object.keys(chart.data[0] ?? {});
    const csv = [
      fields.join(","),
      ...chart.data.map((row) => fields.map((field) => JSON.stringify(row[field] ?? "")).join(",")),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${chart.id}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  return chart.data.length ? (
    <button className="csv-download" type="button" onClick={download}>
      Download CSV
    </button>
  ) : null;
}
