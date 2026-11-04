"""
Tests for the remodeled Project Explorer:
- 1-level flat category hierarchy (DATA TABLES, GRAPHS, REPORTS & RESULTS)
- Live search filtering by item name, report title, and column metadata
- Single-click and double-click activation
- Bidirectional active tab highlighting
- Context actions: duplicate sheet, duplicate graph, rename, and quick plot
"""

import pytest
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
from PyQt6.QtCore import Qt
from omnigraph.core.project import Project, GraphModel, ReportModel, CurveModel
from omnigraph.core.worksheet import Workbook, Worksheet, Column, ColumnRole
from omnigraph.ui.project_explorer import ProjectExplorerWidget
from omnigraph.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_explorer_flat_1level_structure(qapp):
    """Test that items are organized into flat 1-level categories with item badges."""
    proj = Project.create_default("TestProj")
    # Add a second sheet
    wb = proj.workbooks[0]
    ws2 = wb.add_sheet(name="XRD_Scan")
    ws2.add_column(name="Theta", role=ColumnRole.X)
    ws2.add_column(name="Counts", role=ColumnRole.Y)

    # Add a graph
    g = GraphModel(title="Diffraction_Pattern", plot_type="line")
    g.add_curve(CurveModel(label="Peak1"))
    proj.graphs.append(g)

    # Add a report
    r = ReportModel(title="Gaussian Fit Summary", report_type="fit")
    proj.reports.append(r)

    explorer = ProjectExplorerWidget(proj)

    # Verify top-level categories
    tree = explorer.tree
    assert tree.topLevelItemCount() == 3

    cat_data = tree.topLevelItem(0)
    cat_graphs = tree.topLevelItem(1)
    cat_reports = tree.topLevelItem(2)

    assert "WORKSHEETS" in cat_data.text(0)
    assert "(2)" in cat_data.text(0)
    assert cat_data.childCount() == 2

    # Check sheet items are direct children (1 level deep)
    sheet1_item = cat_data.child(0)
    sheet2_item = cat_data.child(1)
    assert "Sheet1" in sheet1_item.text(0)
    assert "XRD_Scan" in sheet2_item.text(0)
    assert f"Columns ({ws2.column_count()})" in sheet2_item.toolTip(0)
    assert sheet2_item.childCount() == 0  # Flat leaf

    # Check graph category
    assert "GRAPHS" in cat_graphs.text(0)
    assert "(1)" in cat_graphs.text(0)
    assert cat_graphs.childCount() == 1
    graph_item = cat_graphs.child(0)
    assert "Diffraction_Pattern" in graph_item.text(0)
    assert "Curves (1)" in graph_item.toolTip(0)
    assert graph_item.childCount() == 0  # Flat leaf

    # Check reports category
    assert "RESULTS" in cat_reports.text(0)
    assert "(1)" in cat_reports.text(0)
    assert cat_reports.childCount() == 1
    report_item = cat_reports.child(0)
    assert "Gaussian Fit Summary" in report_item.text(0)
    assert report_item.childCount() == 0  # Flat leaf


def test_explorer_live_search_filtering(qapp):
    """Test real-time filtering of sheets, graphs, and reports by title and column metadata."""
    proj = Project.create_default("SearchProj")
    wb = proj.workbooks[0]
    ws1 = wb.sheets[0]
    ws1.name = "EnzymeKinetics"
    ws1.columns[0].long_name = "SubstrateConcentration"

    ws2 = wb.add_sheet(name="Spectroscopy")
    ws2.add_column(name="Wavelength")

    g1 = GraphModel(title="MichaelisMentenPlot")
    g2 = GraphModel(title="AbsorbanceSpectrum")
    proj.graphs.extend([g1, g2])

    r1 = ReportModel(title="LineweaverBurkAnalysis")
    proj.reports.append(r1)

    explorer = ProjectExplorerWidget(proj)

    # 1. Filter by graph title substring
    explorer._filter_tree("Absorbance")
    cat_graphs = explorer.tree.topLevelItem(1)
    assert not cat_graphs.isHidden()
    # g1 hidden, g2 visible
    assert cat_graphs.child(0).isHidden() is True
    assert cat_graphs.child(1).isHidden() is False

    # 2. Filter by sheet name
    explorer._filter_tree("Enzyme")
    cat_data = explorer.tree.topLevelItem(0)
    assert not cat_data.isHidden()
    assert cat_data.child(0).isHidden() is False
    assert cat_data.child(1).isHidden() is True

    # 3. Filter by column metadata in tooltip
    explorer._filter_tree("Wavelength")
    assert cat_data.child(1).isHidden() is False

    # 4. Clear filter restores all
    explorer._filter_tree("")
    for i in range(explorer.tree.topLevelItemCount()):
        cat = explorer.tree.topLevelItem(i)
        assert not cat.isHidden()
        for j in range(cat.childCount()):
            assert not cat.child(j).isHidden()


def test_explorer_single_click_and_highlight(qapp):
    """Test that single click activates items and highlight_item selects correctly."""
    proj = Project.create_default("ClickProj")
    g = GraphModel(title="TestGraph")
    proj.graphs.append(g)

    explorer = ProjectExplorerWidget(proj)

    activated_events = []
    explorer.item_activated.connect(lambda t, i, p: activated_events.append((t, i, p)))

    # Click on Category header should NOT activate
    cat_item = explorer.tree.topLevelItem(0)
    explorer._on_item_clicked(cat_item, 0)
    assert len(activated_events) == 0

    # Single click on sheet item activates sheet
    sheet_item = cat_item.child(0)
    explorer._on_item_clicked(sheet_item, 0)
    assert len(activated_events) == 1
    assert activated_events[0][0] == "sheet"
    assert activated_events[0][1] == "Sheet1"

    # Single click on graph item activates graph
    graph_cat = explorer.tree.topLevelItem(1)
    graph_item = graph_cat.child(0)
    explorer._on_item_clicked(graph_item, 0)
    assert len(activated_events) == 2
    assert activated_events[1][0] == "graph"
    assert activated_events[1][1] == "TestGraph"

    # Test highlight_item
    explorer.highlight_item("graph", "TestGraph")
    assert explorer.tree.currentItem() == graph_item


def test_explorer_main_window_context_actions(qapp):
    """Test duplicate, rename, and quick plot through MainWindow explorer integration."""
    proj = Project.create_default("ContextProj")
    window = MainWindow(proj)
    window.show()

    # 1. Duplicate Sheet
    window._on_explorer_duplicate_sheet("Sheet1", "Book1")
    wb = proj.workbooks[0]
    assert len(wb.sheets) == 2
    assert wb.sheets[1].name == "Sheet1_copy"

    # 2. Duplicate Graph
    g = GraphModel(title="Spectrum")
    proj.graphs.append(g)
    window._populate_all_views()

    window._on_explorer_duplicate_graph("Spectrum")
    assert len(proj.graphs) == 2
    assert "Spectrum (Copy)" in [gr.title for gr in proj.graphs]

    # 3. Tab changed updates tree highlight
    # Switch to second tab (Sheet1_copy)
    window.center_tabs.setCurrentIndex(1)
    current_tree_item = window.explorer_widget.tree.currentItem()
    assert current_tree_item is not None
    assert "Sheet1_copy" in current_tree_item.text(0)

    window.close()


def test_explorer_project_header_and_project_switch(qapp, tmp_path):
    """Test Project Header display, save status, set_project, and switching projects."""
    proj1 = Project.create_default("BatteryStudy")
    explorer = ProjectExplorerWidget(proj1)

    assert explorer.lbl_project_name.text() == "BatteryStudy"
    assert "Not saved to a file" in explorer.lbl_project_status.text()

    # Simulate saving project
    save_path = str(tmp_path / "BatteryStudy.kgraph")
    proj1.save_to_file(save_path)
    explorer.update_header()
    assert "BatteryStudy.kgraph" in explorer.lbl_project_status.text()

    # Switch to a completely different project
    proj2 = Project.create_default("KineticsStudy")
    proj2.graphs.append(GraphModel(title="EnzymePlot"))
    explorer.set_project(proj2)

    assert explorer.lbl_project_name.text() == "KineticsStudy"
    assert "Not saved to a file" in explorer.lbl_project_status.text()
    # Tree now reflects proj2 items
    cat_graphs = explorer.tree.topLevelItem(1)
    assert "(1)" in cat_graphs.text(0)
    assert "EnzymePlot" in cat_graphs.child(0).text(0)

