import os
import pytest
from omnigraph.core.project import Project, GraphModel, CurveModel, ReportModel
from omnigraph.core.worksheet import Workbook, Worksheet, Column, ColumnRole
from omnigraph.ui.samples import SampleProjects


def test_sample_project_creation_and_save_load(tmp_path):
    # Test all 4 scientific sample projects
    samples = [
        SampleProjects.create_spectroscopy_sample(),
        SampleProjects.create_enzyme_kinetics_sample(),
        SampleProjects.create_dose_response_sample(),
        SampleProjects.create_dual_axis_sample(),
    ]

    for i, proj in enumerate(samples):
        filepath = str(tmp_path / f"sample_{i}.kgraph")
        proj.save_to_file(filepath)
        assert os.path.exists(filepath)

        loaded = Project.load_from_file(filepath)
        assert loaded.name == proj.name
        assert len(loaded.workbooks) == len(proj.workbooks)
        assert len(loaded.graphs) == len(proj.graphs)
        assert loaded.graphs[0].title == proj.graphs[0].title
        assert len(loaded.graphs[0].curves) == len(proj.graphs[0].curves)
