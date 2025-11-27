# app/app_shiny.py

from shiny import App, ui, render, reactive
import pandas as pd
from pathlib import Path
import sys
import folium
import html as html_lib  # for escaping map HTML into an iframe srcdoc

# Make src importable when running `python -m shiny run app/app_shiny.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.load_assets import load_assets
from src.vulnerability import compute_vulnerability


app_ui = ui.page_fluid(
    # ---- Global typography tweaks -----------------------------------------
    ui.tags.style(
        """
        /* Global base font */
        body {
            font-size: 16px !important;
        }

        /* Card titles like 'Filters', 'Asset Vulnerability Map' */
        .card h4 {
            font-size: 1.15rem !important;
            font-weight: 600;
        }

        /* Labels for inputs */
        .shiny-input-container label,
        .shiny-input-container .form-label,
        .shiny-input-container .control-label {
            font-size: 1.05rem !important;
        }

        /* Inputs and selects */
        .shiny-input-container .form-select,
        .shiny-input-container .form-control,
        .shiny-input-container input,
        .shiny-input-container select {
            font-size: 1.0rem !important;
        }

        /* Help text inside cards */
        .card .help-text,
        .card .form-text,
        .card p,
        .card small {
            font-size: 0.95rem !important;
        }

        /* Data table text */
        table {
            font-size: 0.95rem !important;
        }

        /* Small colored squares for legend */
        .legend-swatch {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 1px solid #555;
            margin-right: 4px;
            vertical-align: middle;
        }

        .legend-item {
            display: inline-flex;
            align-items: center;
            margin-right: 12px;
            margin-bottom: 4px;
            font-size: 0.9rem;
        }

        /* Reduce vertical spacing before legend */
        .legend-container {
            margin-top: 4px !important;
        }
        """
    ),

    ui.h2("Climate Stress Vulnerability — Infrastructure Assets"),

    # ---- GLOBAL CONTROLS: SCENARIO ----------------------------------------
    ui.row(
        ui.column(
            4,
            ui.card(
                ui.input_select(
                    "scenario",
                    "Climate scenario",
                    choices=[
                        "2020",
                        "2030",
                        "2050",
                        "2080",
                    ],
                    selected="2020",
                ),
            ),
        ),
        ui.column(
            8,
            ui.help_text(
                "Scenario selects which set of climate hazard indices "
                "to use from data/hazards.csv (e.g., 2020 vs 2050). "
                "If a scenario has no data, exposure defaults to medium (0.5)."
            ),
        ),
    ),

    ui.br(),

    ui.navset_tab(
        # ---- TAB 1: TABLE VIEW --------------------------------------------
        ui.nav_panel(
            "Table",
            ui.row(
                ui.column(
                    4,
                    ui.card(
                        ui.h4("Filters"),
                        ui.input_select(
                            "asset_type",
                            "Asset type",
                            choices=["All", "transformer", "substation", "building"],
                            selected="All",
                        ),
                        ui.input_slider(
                            "min_vuln",
                            "Minimum vulnerability score",
                            min=0,
                            max=100,
                            value=0,
                            step=5,
                        ),
                        ui.help_text(
                            "Vulnerability is a composite index combining exposure, "
                            "sensitivity, and criticality. Scores range from 0 (low) "
                            "to 100 (high)."
                        ),
                    ),
                ),
                ui.column(
                    8,
                    ui.card(
                        ui.h4("Asset Vulnerability Table"),
                        ui.output_table("vuln_table"),
                    ),
                ),
            ),
        ),

        # ---- TAB 2: MAP VIEW ----------------------------------------------
        ui.nav_panel(
            "Map",
            ui.row(
                ui.column(
                    4,
                    ui.card(
                        ui.h4("Filters"),
                        ui.input_select(
                            "asset_type_map",
                            "Asset type",
                            choices=["All", "transformer", "substation", "building"],
                            selected="All",
                        ),
                        ui.input_slider(
                            "min_vuln_map",
                            "Minimum vulnerability score",
                            min=0,
                            max=100,
                            value=0,
                            step=5,
                        ),
                        ui.input_select(
                            "map_color_by",
                            "Color markers by",
                            choices={
                                "vulnerability_score": "Vulnerability index",
                                "multi_hazard_index": "Multi-hazard index (selected hazards)",
                                "heat_index": "Heat hazard",
                                "freeze_thaw": "Freeze–thaw cycles",
                                "heavy_rain": "Heavy rain",
                                "flood_risk": "Flood risk",
                                "wind_extreme": "Extreme wind",
                            },
                            selected="vulnerability_score",
                        ),
                        ui.input_checkbox_group(
                            "hazards_included",
                            "Hazards in multi-hazard index",
                            choices={
                                "heat_index": "Heat hazard",
                                "flood_risk": "Flood risk",
                                "heavy_rain": "Heavy rain",
                                "freeze_thaw": "Freeze–thaw cycles",
                                "wind_extreme": "Extreme wind",
                            },
                            selected=["heat_index", "flood_risk", "heavy_rain"],
                        ),
                        ui.help_text(
                            "Markers are colored using a 0–100 score. "
                            "For 'Multi-hazard index', the score is computed from "
                            "the selected hazards."
                        ),
                    ),
                ),
                ui.column(
                    8,
                    ui.card(
                        ui.h4("Asset Vulnerability Map"),
                        ui.output_ui("map_ui"),

                        # Visual legend with actual colors
                        ui.tags.div(
                            ui.tags.div(
                                ui.tags.span(
                                    class_="legend-swatch",
                                    style="background-color: green;",
                                ),
                                ui.tags.span("< 25"),
                                class_="legend-item",
                            ),
                            ui.tags.div(
                                ui.tags.span(
                                    class_="legend-swatch",
                                    style="background-color: yellow;",
                                ),
                                ui.tags.span("25–50"),
                                class_="legend-item",
                            ),
                            ui.tags.div(
                                ui.tags.span(
                                    class_="legend-swatch",
                                    style="background-color: orange;",
                                ),
                                ui.tags.span("50–75"),
                                class_="legend-item",
                            ),
                            ui.tags.div(
                                ui.tags.span(
                                    class_="legend-swatch",
                                    style="background-color: red;",
                                ),
                                ui.tags.span("≥ 75"),
                                class_="legend-item",
                            ),
                            ui.tags.div(
                                ui.tags.small(
                                    "Score scale is 0–100 (vulnerability or selected hazard index)."
                                ),
                                class_="mt-1",
                            ),
                            class_="legend-container",
                        ),
                    ),
                ),
            ),
        ),

        # ---- TAB 3: DOWNLOAD VIEW -----------------------------------------
        ui.nav_panel(
            "Download",
            ui.row(
                ui.column(
                    4,
                    ui.card(
                        ui.h4("Download options"),
                        ui.input_radio_buttons(
                            "download_source",
                            "Data to download",
                            choices={
                                "table": "Filtered table (Table tab filters)",
                                "map": "Filtered map assets (Map tab filters)",
                            },
                            selected="table",
                        ),
                        ui.input_select(
                            "download_format",
                            "Format",
                            choices={"csv": "CSV"},
                            selected="csv",
                        ),
                        ui.download_button("download_btn", "Download data"),
                        ui.help_text(
                            "Download reflects current filters, scenario, and (for "
                            "map data) the map filters."
                        ),
                    ),
                ),
                ui.column(
                    8,
                    ui.card(
                        ui.h4("Preview of data to be downloaded"),
                        ui.output_table("download_preview"),
                    ),
                ),
            ),
        ),
    ),
)


def server(input, output, session):
    # ---- Current scenario (reactive) ---------------------------------------
    @reactive.Calc
    def current_scenario() -> str:
        return input.scenario()

    # Hazards selected for the multi-hazard index
    @reactive.Calc
    def hazards_selected() -> list[str]:
        # Returns a list like ["heat_index", "flood_risk", ...]
        return list(input.hazards_included())

    # ---- Base data with vulnerability + multi-hazard index ----------------
    @reactive.Calc
    def assets_with_vuln() -> pd.DataFrame:
        df = load_assets()
        scen = current_scenario()
        df_v = compute_vulnerability(df, scenario=scen)

        # Compute multi-hazard index from selected hazards (0–1 scale)
        selected = hazards_selected()
        valid_cols = [c for c in selected if c in df_v.columns]

        if valid_cols:
            # Average of selected hazard columns (assumed 0–1)
            df_v["multi_hazard_index"] = df_v[valid_cols].mean(axis=1)
        else:
            # If nothing selected, set to 0
            df_v["multi_hazard_index"] = 0.0

        return df_v

    # ---- Table filters -----------------------------------------------------
    @reactive.Calc
    def filtered_assets_table() -> pd.DataFrame:
        df = assets_with_vuln()

        asset_type = input.asset_type()
        if asset_type != "All":
            df = df[df["type"] == asset_type]

        min_vuln = input.min_vuln()
        df = df[df["vulnerability_score"] >= min_vuln]

        df = df.sort_values("vulnerability_score", ascending=False)

        cols = [
            "asset_id",
            "type",
            "latitude",
            "longitude",
            "capacity_kVA",
            "age_years",
            "criticality",
            "exposure",
            "sensitivity",
            "criticality_norm",
            "vulnerability_score",
            "multi_hazard_index",
        ]
        cols = [c for c in cols if c in df.columns]
        return df[cols]

    @output
    @render.table
    def vuln_table():
        return filtered_assets_table()

    # ---- Map filters -------------------------------------------------------
    @reactive.Calc
    def filtered_assets_map() -> pd.DataFrame:
        df = assets_with_vuln()

        asset_type = input.asset_type_map()
        if asset_type != "All":
            df = df[df["type"] == asset_type]

        min_vuln = input.min_vuln_map()
        df = df[df["vulnerability_score"] >= min_vuln]

        return df

    @reactive.Calc
    def map_color_var() -> str:
        return input.map_color_by()

    # ---- Map rendering (sandboxed in iframe) -------------------------------
    @output
    @render.ui
    def map_ui():
        df = filtered_assets_map()

        if df.empty:
            return ui.p("No assets match the current filters.")

        color_var = map_color_var()
        if color_var not in df.columns:
            color_var = "vulnerability_score"

        center_lat = df["latitude"].mean()
        center_lon = df["longitude"].mean()

        # GREY BASEMAP so marker colors stand out
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles="CartoDB positron",
        )

        def color_for_score(score: float) -> str:
            if score >= 75:
                return "red"
            elif score >= 50:
                return "orange"
            elif score >= 25:
                return "yellow"
            else:
                return "green"

        var_labels = {
            "vulnerability_score": "Vulnerability",
            "multi_hazard_index": "Multi-hazard index",
            "heat_index": "Heat hazard",
            "freeze_thaw": "Freeze–thaw",
            "heavy_rain": "Heavy rain",
            "flood_risk": "Flood risk",
            "wind_extreme": "Extreme wind",
        }
        var_label = var_labels.get(color_var, color_var)

        for _, row in df.iterrows():
            raw_value = float(row[color_var])

            # vulnerability_score is 0–100; others are 0–1
            if color_var == "vulnerability_score":
                score_0_100 = raw_value
                display_value = f"{raw_value:.1f}"
            else:
                score_0_100 = raw_value * 100.0
                display_value = f"{raw_value:.2f}"

            color = color_for_score(score_0_100)

            popup_html = (
                f"<b>{row['asset_id']}</b> ({row['type']})<br>"
                f"{var_label}: {display_value}<br>"
                f"Vulnerability score: {row['vulnerability_score']:.1f}<br>"
                f"Multi-hazard index: {row.get('multi_hazard_index', 0.0):.2f}<br>"
                f"Capacity: {row['capacity_kVA']} kVA<br>"
                f"Age: {row['age_years']} years<br>"
                f"Criticality: {row['criticality']}"
            )

            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(m)

        # Full HTML for the map
        map_html = m.get_root().render()

        # Remove the Jupyter trust banner if present
        map_html = map_html.replace(
            "Make this Notebook Trusted to load map: File -> Trust Notebook",
            ""
        )

        # Wrap Folium HTML in an iframe via srcdoc so its CSS is sandboxed
        iframe_html = (
            '<iframe srcdoc="{srcdoc}" '
            'style="width:100%;height:600px;border:none;overflow:hidden;"></iframe>'
        ).format(srcdoc=html_lib.escape(map_html))

        return ui.HTML(iframe_html)

    # ---- Download logic ----------------------------------------------------
    @reactive.Calc
    def download_df() -> pd.DataFrame:
        source = input.download_source()
        if source == "map":
            return filtered_assets_map()
        else:
            return filtered_assets_table()

    @output
    @render.table
    def download_preview():
        df = download_df()
        # Small preview so it doesn't get unwieldy
        return df.head(20)

    @output
    @render.download(filename="climate_infra_risk_data.csv")
    def download_btn():
        df = download_df()
        # Only CSV for now
        return df.to_csv(index=False).encode("utf-8")


app = App(app_ui, server)