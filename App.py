import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors


# ============================================================
# PAGE
# ============================================================
st.set_page_config(page_title="2D Rectangle Array Generator", layout="wide")
st.title("2D Rectangle Array Generator")
st.caption(
    "Atur ukuran rectangle, jumlah array, dimensi outer boundary, "
    "dan clearance secara terpisah."
)


# ============================================================
# DIMENSION LINE HELPERS - PLOTLY
# ============================================================
def add_hdim(fig, x1, x2, y, ext_y, label, color="gray"):
    # Extension lines: dashed
    fig.add_shape(type="line", x0=x1, y0=ext_y, x1=x1, y1=y,
                  line=dict(color=color, width=1, dash="dash"))
    fig.add_shape(type="line", x0=x2, y0=ext_y, x1=x2, y1=y,
                  line=dict(color=color, width=1, dash="dash"))
    # Dimension line: solid
    fig.add_shape(type="line", x0=x1, y0=y, x1=x2, y1=y,
                  line=dict(color=color, width=1.5))
    fig.add_annotation(x=(x1+x2)/2, y=y, text=label, showarrow=False,
                       font=dict(color=color, size=11),
                       bgcolor="white", borderpad=2, yshift=10)


def add_vdim(fig, y1, y2, x, ext_x, label, color="gray"):
    fig.add_shape(type="line", x0=ext_x, y0=y1, x1=x, y1=y1,
                  line=dict(color=color, width=1, dash="dash"))
    fig.add_shape(type="line", x0=ext_x, y0=y2, x1=x, y1=y2,
                  line=dict(color=color, width=1, dash="dash"))
    fig.add_shape(type="line", x0=x, y0=y1, x1=x, y1=y2,
                  line=dict(color=color, width=1.5))
    fig.add_annotation(x=x, y=(y1+y2)/2, text=label, showarrow=False,
                       textangle=-90, font=dict(color=color, size=11),
                       bgcolor="white", borderpad=2, xshift=-12)


# ============================================================
# INPUT 1: RECTANGLE
# ============================================================
st.sidebar.header("1. Rectangle")

input_mode = st.sidebar.radio(
    "Input Method",
    ["Dimensions", "Coordinate"]
)

if input_mode == "Dimensions":
    dimension_x = st.sidebar.number_input(
        "Rectangle Dimension X (mm)", min_value=0.1,
        value=100.0, step=1.0
    )
    dimension_y = st.sidebar.number_input(
        "Rectangle Dimension Y (mm)", min_value=0.1,
        value=50.0, step=1.0
    )
else:
    st.sidebar.caption("Masukkan dua titik diagonal rectangle.")
    coord_x1 = st.sidebar.number_input("Coordinate X1 (mm)", value=0.0, step=1.0)
    coord_y1 = st.sidebar.number_input("Coordinate Y1 (mm)", value=0.0, step=1.0)
    coord_x2 = st.sidebar.number_input("Coordinate X2 (mm)", value=100.0, step=1.0)
    coord_y2 = st.sidebar.number_input("Coordinate Y2 (mm)", value=50.0, step=1.0)
    dimension_x = abs(coord_x2 - coord_x1)
    dimension_y = abs(coord_y2 - coord_y1)

# ============================================================
# INPUT 2: ARRAY
# ============================================================
st.sidebar.header("2. Array")

count_x = int(st.sidebar.number_input(
    "Count X", min_value=1, value=3, step=1
))
count_y = int(st.sidebar.number_input(
    "Count Y", min_value=1, value=2, step=1
))
spacing_x = st.sidebar.number_input(
    "Spacing X (mm)", min_value=0.0, value=10.0, step=1.0
)
spacing_y = st.sidebar.number_input(
    "Spacing Y (mm)", min_value=0.0, value=10.0, step=1.0
)

# ============================================================
# INPUT 3: OUTER BOUNDARY - INDEPENDENT SIZE + CLEARANCE
# ============================================================
st.sidebar.header("3. Outer Boundary")

boundary_origin_x = st.sidebar.number_input(
    "Boundary Origin X (mm)", value=0.0, step=1.0
)
boundary_origin_y = st.sidebar.number_input(
    "Boundary Origin Y (mm)", value=0.0, step=1.0
)

boundary_width = st.sidebar.number_input(
    "Outer Boundary Dimension X (mm)",
    min_value=0.1, value=350.0, step=1.0
)
boundary_height = st.sidebar.number_input(
    "Outer Boundary Dimension Y (mm)",
    min_value=0.1, value=180.0, step=1.0
)

st.sidebar.caption(
    "Clearance X/Y di bawah ini adalah jarak dari sisi kiri/bawah "
    "outer boundary menuju awal array. Clearance sisi kanan/atas dihitung otomatis."
)
clearance_x = st.sidebar.number_input(
    "Clearance X - Left (mm)", min_value=0.0, value=10.0, step=1.0
)
clearance_y = st.sidebar.number_input(
    "Clearance Y - Bottom (mm)", min_value=0.0, value=10.0, step=1.0
)


# ============================================================
# CALCULATIONS AND VALIDATION
# ============================================================
if dimension_x <= 0 or dimension_y <= 0:
    st.error("Dimension rectangle harus lebih besar dari 0.")
    st.stop()

array_width = dimension_x * count_x + spacing_x * (count_x - 1)
array_height = dimension_y * count_y + spacing_y * (count_y - 1)

# Boundary coordinates are independently controlled
boundary_x1 = boundary_origin_x
boundary_y1 = boundary_origin_y
boundary_x2 = boundary_origin_x + boundary_width
boundary_y2 = boundary_origin_y + boundary_height

# Clearance positions the array inside the boundary
array_x1 = boundary_x1 + clearance_x
array_y1 = boundary_y1 + clearance_y
array_x2 = array_x1 + array_width
array_y2 = array_y1 + array_height

clearance_right = boundary_x2 - array_x2
clearance_top = boundary_y2 - array_y2

if clearance_right < -1e-9 or clearance_top < -1e-9:
    st.error(
        "Array tidak muat di dalam outer boundary. "
        f"Array membutuhkan {array_width:g} × {array_height:g} mm, "
        f"sedangkan ruang setelah clearance kiri/bawah hanya "
        f"{boundary_width-clearance_x:g} × "
        f"{boundary_height-clearance_y:g} mm. "
        "Perbesar outer boundary atau kurangi clearance/jumlah/ukuran rectangle."
    )
    st.stop()


# ============================================================
# GENERATE RECTANGLES
# ============================================================
rectangles = []
for row in range(count_y):
    for col in range(count_x):
        x1 = array_x1 + col * (dimension_x + spacing_x)
        y1 = array_y1 + row * (dimension_y + spacing_y)
        x2 = x1 + dimension_x
        y2 = y1 + dimension_y
        rectangles.append({
            "Rectangle": f"R{row+1}-{col+1}",
            "Row": row + 1,
            "Column": col + 1,
            "X1": x1,
            "Y1": y1,
            "X2": x2,
            "Y2": y2,
            "Dimension X": dimension_x,
            "Dimension Y": dimension_y
        })

df = pd.DataFrame(rectangles)


# ============================================================
# SUMMARY
# ============================================================
st.subheader("Dimension Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rectangle Count", count_x * count_y)
c2.metric("Array Size", f"{array_width:g} × {array_height:g} mm")
c3.metric("Outer Boundary", f"{boundary_width:g} × {boundary_height:g} mm")
c4.metric("Remaining Clearance", f"{clearance_right:g} / {clearance_top:g} mm")

with st.expander("Detail ukuran dan clearance"):
    detail = pd.DataFrame({
        "Parameter": [
            "Rectangle Dimension X", "Rectangle Dimension Y",
            "Spacing X", "Spacing Y",
            "Array Dimension X", "Array Dimension Y",
            "Outer Boundary Dimension X", "Outer Boundary Dimension Y",
            "Clearance Left (X)", "Clearance Right (X)",
            "Clearance Bottom (Y)", "Clearance Top (Y)"
        ],
        "Value (mm)": [
            dimension_x, dimension_y, spacing_x, spacing_y,
            array_width, array_height, boundary_width, boundary_height,
            clearance_x, clearance_right, clearance_y, clearance_top
        ]
    })
    st.dataframe(detail, use_container_width=True, hide_index=True)


# ============================================================
# PLOTLY VIEW
# ============================================================
st.subheader("2D Layout")
fig = go.Figure()

# Rectangle array
for item in rectangles:
    fig.add_shape(
        type="rect",
        x0=item["X1"], y0=item["Y1"],
        x1=item["X2"], y1=item["Y2"],
        line=dict(color="#2878B5", width=2),
        fillcolor="rgba(40,120,181,0.06)"
    )
    fig.add_annotation(
        x=(item["X1"]+item["X2"])/2,
        y=(item["Y1"]+item["Y2"])/2,
        text=item["Rectangle"], showarrow=False,
        font=dict(size=10, color="#2878B5")
    )

# Outer boundary
fig.add_shape(
    type="rect",
    x0=boundary_x1, y0=boundary_y1,
    x1=boundary_x2, y1=boundary_y2,
    line=dict(color="green", width=2),
    fillcolor="rgba(0,0,0,0)"
)

# Rectangle dimension X and Y (first rectangle)
add_hdim(
    fig, array_x1, array_x1 + dimension_x,
    array_y2 + dimension_y*0.22, array_y2,
    f"{dimension_x:g} mm", "gray"
)
add_vdim(
    fig, array_y1, array_y1 + dimension_y,
    array_x1 - dimension_x*0.22, array_x1,
    f"{dimension_y:g} mm", "gray"
)

# Spacing X: between first and second rectangle
if count_x > 1 and spacing_x > 0:
    add_hdim(
        fig, array_x1 + dimension_x,
        array_x1 + dimension_x + spacing_x,
        boundary_y1 - dimension_y*0.25, array_y1,
        f"{spacing_x:g} mm", "#E67E22"
    )

# Spacing Y: between first and second row
if count_y > 1 and spacing_y > 0:
    add_vdim(
        fig, array_y1 + dimension_y,
        array_y1 + dimension_y + spacing_y,
        boundary_x1 - dimension_x*0.25, array_x1,
        f"{spacing_y:g} mm", "#E67E22"
    )

# Outer boundary dimensions
boundary_dim_y = boundary_y1 - dimension_y*0.65
boundary_dim_x = boundary_x2 + dimension_x*0.65
add_hdim(
    fig, boundary_x1, boundary_x2, boundary_dim_y,
    boundary_y1, f"{boundary_width:g} mm", "green"
)
add_vdim(
    fig, boundary_y1, boundary_y2, boundary_dim_x,
    boundary_x2, f"{boundary_height:g} mm", "green"
)

left = min(boundary_x1 - dimension_x*0.8,
           boundary_x1 - dimension_x*0.25 - dimension_x*0.6)
right = boundary_x2 + dimension_x*1.0
bottom = boundary_y1 - dimension_y*1.15
top = max(boundary_y2 + dimension_y*0.25,
          array_y2 + dimension_y*0.7)

fig.update_layout(
    height=700,
    margin=dict(l=25, r=25, t=25, b=25),
    showlegend=False,
    plot_bgcolor="white",
    xaxis=dict(title="X (mm)", range=[left, right], zeroline=False),
    yaxis=dict(title="Y (mm)", range=[bottom, top],
               scaleanchor="x", scaleratio=1, zeroline=False)
)
fig.update_xaxes(showgrid=True, gridcolor="#EAEAEA")
fig.update_yaxes(showgrid=True, gridcolor="#EAEAEA")
st.plotly_chart(fig, use_container_width=True)


# ============================================================
# COORDINATE TABLE + CSV
# ============================================================
st.subheader("Rectangle Coordinates")
st.dataframe(df, use_container_width=True, hide_index=True)

st.download_button(
    "Download Coordinates CSV",
    data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name="rectangle_coordinates.csv",
    mime="text/csv"
)


# ============================================================
# PDF EXPORT
# Clean diagram: no axes, no ticks, no grid, no coordinate numbers
# ============================================================
def create_pdf():
    output = BytesIO()

    fig_pdf, ax = plt.subplots(figsize=(11, 6))

    # Rectangles and labels
    for item in rectangles:
        ax.add_patch(Rectangle(
            (item["X1"], item["Y1"]),
            dimension_x, dimension_y,
            linewidth=1.5, edgecolor="#2878B5", facecolor="none"
        ))
        ax.text(
            (item["X1"]+item["X2"])/2,
            (item["Y1"]+item["Y2"])/2,
            item["Rectangle"], ha="center", va="center",
            fontsize=8, color="#2878B5"
        )

    # Outer boundary
    ax.add_patch(Rectangle(
        (boundary_x1, boundary_y1),
        boundary_width, boundary_height,
        linewidth=1.8, edgecolor="green", facecolor="none"
    ))

    # PDF dimension helpers
    def hdim_pdf(x1, x2, y, ext_y, label, color="gray"):
        ax.plot([x1, x1], [ext_y, y], color=color,
                linewidth=0.8, linestyle="--")
        ax.plot([x2, x2], [ext_y, y], color=color,
                linewidth=0.8, linestyle="--")
        ax.annotate(
            "", xy=(x2, y), xytext=(x1, y),
            arrowprops=dict(arrowstyle="<->", color=color, linewidth=1)
        )
        ax.text(
            (x1+x2)/2, y, label, ha="center", va="bottom",
            fontsize=8, color=color,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5)
        )

    def vdim_pdf(y1, y2, x, ext_x, label, color="gray"):
        ax.plot([ext_x, x], [y1, y1], color=color,
                linewidth=0.8, linestyle="--")
        ax.plot([ext_x, x], [y2, y2], color=color,
                linewidth=0.8, linestyle="--")
        ax.annotate(
            "", xy=(x, y2), xytext=(x, y1),
            arrowprops=dict(arrowstyle="<->", color=color, linewidth=1)
        )
        ax.text(
            x, (y1+y2)/2, label, ha="left", va="center",
            rotation=90, fontsize=8, color=color,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5)
        )

    # Rectangle dimensions
    hdim_pdf(
        array_x1, array_x1+dimension_x,
        array_y2+dimension_y*0.22, array_y2,
        f"{dimension_x:g} mm"
    )
    vdim_pdf(
        array_y1, array_y1+dimension_y,
        array_x1-dimension_x*0.22, array_x1,
        f"{dimension_y:g} mm"
    )

    # Spacing dimensions
    if count_x > 1 and spacing_x > 0:
        hdim_pdf(
            array_x1+dimension_x,
            array_x1+dimension_x+spacing_x,
            boundary_y1-dimension_y*0.25, array_y1,
            f"{spacing_x:g} mm", "#E67E22"
        )
    if count_y > 1 and spacing_y > 0:
        vdim_pdf(
            array_y1+dimension_y,
            array_y1+dimension_y+spacing_y,
            boundary_x1-dimension_x*0.25, array_x1,
            f"{spacing_y:g} mm", "#E67E22"
        )

    # Boundary dimensions
    hdim_pdf(
        boundary_x1, boundary_x2,
        boundary_y1-dimension_y*0.65, boundary_y1,
        f"{boundary_width:g} mm", "green"
    )
    vdim_pdf(
        boundary_y1, boundary_y2,
        boundary_x2+dimension_x*0.65, boundary_x2,
        f"{boundary_height:g} mm", "green"
    )

    # Remove axes/ticks/grid completely
    ax.grid(False)
    ax.set_axis_off()
    ax.set_xlim(
        min(boundary_x1-dimension_x*0.9,
            boundary_x1-dimension_x*0.25-dimension_x*0.7),
        boundary_x2+dimension_x*1.0
    )
    ax.set_ylim(
        boundary_y1-dimension_y*1.2,
        max(boundary_y2+dimension_y*0.3,
            array_y2+dimension_y*0.8)
    )
    ax.set_aspect("equal", adjustable="box")
    fig_pdf.tight_layout()

    image_buf = BytesIO()
    fig_pdf.savefig(
        image_buf, format="png", dpi=220,
        bbox_inches="tight", facecolor="white"
    )
    plt.close(fig_pdf)
    image_buf.seek(0)

    # PDF page 1: layout and parameters
    pagesize = landscape(A4)
    pdf = canvas.Canvas(output, pagesize=pagesize)
    page_w, page_h = pagesize

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(35, page_h-35, "PANEL LAYOUT - RECTANGLE ARRAY")

    info = [
        f"Rectangle Count: {count_x*count_y}",
        f"Rectangle Dimension: {dimension_x:g} x {dimension_y:g} mm",
        f"Spacing X / Y: {spacing_x:g} / {spacing_y:g} mm",
        f"Array Dimension: {array_width:g} x {array_height:g} mm",
        f"Outer Boundary Dimension: {boundary_width:g} x {boundary_height:g} mm",
        f"Boundary Origin: X={boundary_origin_x:g} mm, Y={boundary_origin_y:g} mm",
        f"Clearance Left / Bottom: {clearance_x:g} / {clearance_y:g} mm",
        f"Clearance Right / Top: {clearance_right:g} / {clearance_top:g} mm"
    ]

    pdf.setFont("Helvetica", 9)
    y = page_h-38

    pdf.drawImage(
        ImageReader(image_buf),
        35, 30, width=page_w-70, height=y-35,
        preserveAspectRatio=True, anchor="c", mask="auto"
    )
    pdf.showPage()

    # PDF page 2+: coordinate table
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(35, page_h-35, "Rectangle Coordinates")
    

    table_data = [list(df.columns)]
    for r in df.itertuples(index=False, name=None):
        table_data.append([
            str(r[0]), str(r[1]), str(r[2]),
            f"{r[3]:g}", f"{r[4]:g}", f"{r[5]:g}", f"{r[6]:g}",
            f"{r[7]:g}", f"{r[8]:g}"
        ])

    rows_per_page = 25
    for start in range(0, len(table_data)-1, rows_per_page):
        if start > 0:
            pdf.showPage()
            pdf.setFont("Helvetica-Bold", 15)
            pdf.drawString(35, page_h-35, "Rectangle Coordinates (continued)")

        chunk = [table_data[0]] + table_data[start+1:start+1+rows_per_page]
        table = Table(
            chunk,
            colWidths=[75, 40, 45, 65, 65, 65, 65, 90, 90],
            rowHeights=18,
            repeatRows=1
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        _, table_h = table.wrapOn(pdf, page_w-70, page_h-90)
        table.drawOn(pdf, 35, page_h-60-table_h)

    pdf.save()
    output.seek(0)
    return output.getvalue()


pdf_data = create_pdf()
st.download_button(
    "Download Layout PDF",
    data=pdf_data,
    file_name="rectangle_array_layout.pdf",
    mime="application/pdf"
)
