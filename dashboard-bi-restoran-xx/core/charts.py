"""Grafik Plotly bertema gelap + olive, selaras dengan design token dashboard."""
import plotly.graph_objects as go

# Palet olive/sage untuk seri data.
OLIVE_SEQ = ["#90a857", "#bcc79a", "#6c7d3c", "#d6ddbf",
             "#54632e", "#9fae72", "#eef1e4", "#738a42"]
# Palet RGB cerah khusus titik klaster — sengaja kontras dengan tema hijau.
CLUSTER_COLORS = ["#ff6b6b", "#4ecdc4", "#ffd93d", "#a78bfa", "#ff9f43",
                  "#54a0ff", "#ff6bcb", "#5eead4", "#f97316", "#22d3ee"]
GRID = "#2d3227"
TEXT = "#a4aa94"
PRIMARY = "#90a857"


def cluster_color(c):
    return CLUSTER_COLORS[int(c) % len(CLUSTER_COLORS)]


def _base(fig: go.Figure, height: int = 320) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter, sans-serif", size=12),
        colorway=OLIVE_SEQ, height=height,
        margin=dict(l=12, r=12, t=36, b=12),
        legend=dict(font=dict(color=TEXT), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#1a1d16", font=dict(color="#e9ebe2")),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID,
                     tickfont=dict(color=TEXT))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID,
                     tickfont=dict(color=TEXT))
    return fig


def bar_top_items(df, value="net_sales", n=15):
    """Bar horizontal: n item teratas berdasarkan total `value`."""
    agg = (df.groupby("items", as_index=False)[value].sum()
             .sort_values(value, ascending=True).tail(n))
    fig = go.Figure(go.Bar(
        x=agg[value], y=agg["items"], orientation="h",
        marker=dict(color=PRIMARY), hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>"))
    fig.update_layout(title=f"{n} Item Teratas — total {value}")
    return _base(fig, height=max(320, 22 * len(agg)))


def donut_category(df, value="net_sales"):
    """Donut: kontribusi tiap kategori terhadap total `value`."""
    agg = df.groupby("category", as_index=False)[value].sum().sort_values(value, ascending=False)
    fig = go.Figure(go.Pie(
        labels=agg["category"], values=agg[value], hole=0.55,
        marker=dict(colors=OLIVE_SEQ, line=dict(color="#0d0e0c", width=1.5)),
        textfont=dict(color="#0d0e0c"),
        hovertemplate="%{label}<br>%{value:,.0f} (%{percent})<extra></extra>"))
    fig.update_layout(title=f"Kontribusi Kategori — {value}")
    return _base(fig, height=360)


def line_quantity_by_month(df):
    """Garis + titik: total kuantitas per bulan."""
    if "bulan" not in df.columns:
        return None
    agg = df.groupby("bulan", as_index=False)["quantity"].sum().sort_values("bulan")
    fig = go.Figure(go.Scatter(
        x=agg["bulan"], y=agg["quantity"], mode="lines+markers",
        line=dict(color=PRIMARY, width=2),
        marker=dict(color="#d6ddbf", size=8, line=dict(color=PRIMARY, width=1.5)),
        hovertemplate="%{x}<br>%{y:,.0f} unit<extra></extra>"))
    fig.update_layout(title="Kuantitas Terjual per Bulan")
    return _base(fig, height=320)


def bar_items_in_category(df, category, value="net_sales", n=20):
    """Bar item-item di dalam satu kategori (mode fokus)."""
    sub = df[df["category"] == category]
    agg = (sub.groupby("items", as_index=False)[value].sum()
              .sort_values(value, ascending=True).tail(n))
    fig = go.Figure(go.Bar(
        x=agg[value], y=agg["items"], orientation="h",
        marker=dict(color="#9fae72"), hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>"))
    fig.update_layout(title=f"Item dalam kategori \u201c{category}\u201d — {value}")
    return _base(fig, height=max(300, 22 * len(agg)))


def bar_categories(df, title, value="quantity", n=20, color=None, color_by_cluster=None):
    """Bar horizontal: rincian kategori di dalam satu klaster, diurut total `value`.
    color_by_cluster (opsional) mewarnai bar dengan palet klaster terkait agar
    selaras dengan warna klaster yang dipilih pengguna."""
    agg = (df.groupby("category", as_index=False)[value].sum()
              .sort_values(value, ascending=True).tail(n))
    bar_color = (cluster_color(color_by_cluster) if color_by_cluster is not None
                 else (color or "#9fae72"))
    fig = go.Figure(go.Bar(
        x=agg[value], y=agg["category"], orientation="h",
        marker=dict(color=bar_color),
        hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>"))
    fig.update_layout(title=title)
    return _base(fig, height=max(260, 26 * len(agg)))


def scatter_clusters(df, x, y, cluster_col, title, label_map=None, xlab=None, ylab=None,
                     text_col="items"):
    """Sebaran amatan per klaster — titik diwarnai palet RGB kontras (bukan tema hijau).
    text_col menentukan label hover ('items' untuk menu, 'nota' untuk transaksi)."""
    has_text = text_col in df.columns
    fig = go.Figure()
    for c in sorted(df[cluster_col].unique()):
        d = df[df[cluster_col] == c]
        name = label_map.get(c, f"Klaster {c}") if label_map else f"Klaster {c}"
        fig.add_trace(go.Scatter(
            x=d[x], y=d[y], mode="markers", name=name,
            marker=dict(size=10, color=cluster_color(c), opacity=0.92,
                        line=dict(color="#0d0e0c", width=0.7)),
            text=d[text_col] if has_text else None,
            hovertemplate=("%{text}<br>%{x:,.0f} / %{y:,.0f}<extra></extra>" if has_text
                           else "%{x:,.0f} / %{y:,.0f}<extra></extra>")))
    fig.update_layout(title=title, xaxis_title=xlab or x, yaxis_title=ylab or y)
    return _base(fig, height=440)


def _cluster_series(df, cluster_col, value, agg):
    g = df.groupby(cluster_col)
    s = g.size() if agg == "count" else g[value].sum()
    return s.sort_index()


def bar_clusters(df, cluster_col, title, value=None, agg="count", label_map=None):
    """Diagram batang per klaster (jumlah menu atau total nilai)."""
    s = _cluster_series(df, cluster_col, value, agg)
    cl = list(s.index)
    labels = [label_map.get(c, f"Klaster {c}") if label_map else f"Klaster {c}" for c in cl]
    fig = go.Figure(go.Bar(
        x=labels, y=[s[c] for c in cl],
        marker=dict(color=[cluster_color(c) for c in cl]),
        hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"))
    fig.update_layout(title=title)
    return _base(fig, height=330)


def pie_clusters(df, cluster_col, title, value=None, agg="count", label_map=None):
    """Diagram lingkaran proporsi per klaster (jumlah menu atau total nilai)."""
    s = _cluster_series(df, cluster_col, value, agg)
    cl = list(s.index)
    labels = [label_map.get(c, f"Klaster {c}") if label_map else f"Klaster {c}" for c in cl]
    fig = go.Figure(go.Pie(
        labels=labels, values=[s[c] for c in cl], hole=0.5,
        marker=dict(colors=[cluster_color(c) for c in cl],
                    line=dict(color="#0d0e0c", width=1.5)),
        textfont=dict(color="#0d0e0c"),
        hovertemplate="%{label}<br>%{value:,.0f} (%{percent})<extra></extra>"))
    fig.update_layout(title=title)
    return _base(fig, height=340)


def line_metric_over_k(dfm, ycol, title, ylab, best_k=None, lower_better=False):
    """Garis + titik metrik terhadap K (Elbow/Silhouette/DBI), tandai K terpilih."""
    fig = go.Figure(go.Scatter(
        x=dfm["K"], y=dfm[ycol], mode="lines+markers",
        line=dict(color=PRIMARY, width=2),
        marker=dict(color="#d6ddbf", size=8, line=dict(color=PRIMARY, width=1.5)),
        hovertemplate="K=%{x}<br>%{y:.4g}<extra></extra>"))
    if best_k is not None and best_k in set(dfm["K"]):
        yv = float(dfm.loc[dfm["K"] == best_k, ycol].iloc[0])
        fig.add_trace(go.Scatter(
            x=[best_k], y=[yv], mode="markers", name=f"K terpilih = {best_k}",
            marker=dict(color="#ff6b6b", size=14, symbol="circle-open",
                        line=dict(width=3))))
    fig.update_layout(title=title, xaxis_title="Jumlah klaster (K)", yaxis_title=ylab,
                      showlegend=False)
    fig.update_xaxes(dtick=1)
    return _base(fig, height=300)


def heatmap_corr(df, cols, title):
    """Heatmap korelasi antar-fitur (untuk sisi pengembang)."""
    corr = df[cols].corr().round(2)
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=cols, y=cols, zmin=-1, zmax=1,
        colorscale=[[0, "#54a0ff"], [0.5, "#0d0e0c"], [1, "#ff6b6b"]],
        text=corr.values, texttemplate="%{text}",
        textfont=dict(color="#e9ebe2", size=11),
        colorbar=dict(tickfont=dict(color=TEXT))))
    fig.update_layout(title=title)
    return _base(fig, height=380)


def scatter_pca(coords, labels, title, var1, var2, label_map=None):
    """Sebaran hasil PCA 2 komponen, diwarnai per klaster (palet RGB)."""
    import pandas as pd
    d = pd.DataFrame({"PC1": coords[:, 0], "PC2": coords[:, 1], "cluster": labels})
    fig = go.Figure()
    for c in sorted(d["cluster"].unique()):
        sub = d[d["cluster"] == c]
        name = label_map.get(c, f"Klaster {c}") if label_map else f"Klaster {c}"
        fig.add_trace(go.Scatter(
            x=sub["PC1"], y=sub["PC2"], mode="markers", name=name,
            marker=dict(size=10, color=cluster_color(c), opacity=0.92,
                        line=dict(color="#0d0e0c", width=0.7))))
    fig.update_layout(title=title,
                      xaxis_title=f"PC1 ({var1:.1f}%)", yaxis_title=f"PC2 ({var2:.1f}%)")
    return _base(fig, height=440)


def scatter_pca_3d(coords, labels, title, v1, v2, v3, label_map=None):
    """Sebaran hasil PCA 3 komponen (3D), diwarnai per klaster (palet RGB)."""
    import pandas as pd
    d = pd.DataFrame({"PC1": coords[:, 0], "PC2": coords[:, 1],
                      "PC3": coords[:, 2], "cluster": labels})
    fig = go.Figure()
    for c in sorted(d["cluster"].unique()):
        s = d[d["cluster"] == c]
        name = label_map.get(c, f"Klaster {c}") if label_map else f"Klaster {c}"
        fig.add_trace(go.Scatter3d(
            x=s["PC1"], y=s["PC2"], z=s["PC3"], mode="markers", name=name,
            marker=dict(size=4, color=cluster_color(c), opacity=0.9,
                        line=dict(width=0)),
            hovertemplate="%{x:.2f}, %{y:.2f}, %{z:.2f}<extra></extra>"))
    ax = dict(backgroundcolor="rgba(13,14,12,0.35)", gridcolor=GRID,
              zerolinecolor=GRID, color=TEXT, showbackground=True)
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis=dict(title=f"PC1 ({v1:.1f}%)", **ax),
            yaxis=dict(title=f"PC2 ({v2:.1f}%)", **ax),
            zaxis=dict(title=f"PC3 ({v3:.1f}%)", **ax),
            bgcolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter, sans-serif", size=12),
        legend=dict(font=dict(color=TEXT), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=40, b=0), height=520)
    return fig


def bar_by_hour(df, value="net_sales", title="Pola per Jam Transaksi"):
    """Bar vertikal: total `value` per jam transaksi (0-23). Dipakai panel kontrol
    POV Jam pada halaman Lihat Dataset (KPI insight); jam BUKAN bagian pemodelan."""
    import pandas as pd
    if "datetime" not in df.columns:
        return None
    jam = pd.to_datetime(df["datetime"], errors="coerce").dt.hour
    d = df.assign(_jam=jam).dropna(subset=["_jam"])
    if len(d) == 0:
        return None
    agg = d.groupby("_jam", as_index=False)[value].sum()
    fig = go.Figure(go.Bar(
        x=agg["_jam"], y=agg[value], marker=dict(color=PRIMARY),
        hovertemplate="Jam %{x}:00<br>%{y:,.0f}<extra></extra>"))
    fig.update_layout(title=title)
    fig.update_xaxes(dtick=1, title="Jam")
    return _base(fig, height=300)
