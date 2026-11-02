"""Exercise real features inside the packaged app before publishing it."""
from pathlib import Path
import tempfile


def run_packaged_checks(project):
    import numpy as np
    import pandas as pd
    from PIL import Image
    from omnigraph.analysis.fitting import CurveFitter
    from omnigraph.core.project import Project
    from omnigraph.graphing.plot_manager import PlotManager

    x = np.arange(10, dtype=float)
    fit = CurveFitter.linear_fit(x, 2 * x + 1)
    if not fit.r_squared > 0.999:
        raise RuntimeError("Packaged linear fitting check failed")
    gaussian_x = np.linspace(-10, 10, 100)
    gaussian_y = 2 + 15 * np.exp(-0.5 * ((gaussian_x - 1.5) / 1.8) ** 2)
    fit = CurveFitter.nonlinear_fit(gaussian_x, gaussian_y, model_type="gaussian")
    if not fit.r_squared > 0.99:
        raise RuntimeError("Packaged nonlinear fitting check failed")

    with tempfile.TemporaryDirectory(prefix="Graffy_Smoke_") as temporary:
        folder = Path(temporary)
        project_path = folder / "sample.kgraph"
        project.save_to_file(str(project_path))
        loaded = Project.load_from_file(str(project_path))
        if loaded.name != project.name:
            raise RuntimeError("Packaged project round-trip failed")
        frame = pd.DataFrame({"X": x, "Y": 2 * x + 1})
        for extension in ("csv", "xlsx"):
            filename = folder / f"data.{extension}"
            if extension == "csv":
                frame.to_csv(filename, index=False)
                restored = pd.read_csv(filename)
            else:
                frame.to_excel(filename, index=False)
                restored = pd.read_excel(filename)
            if not np.allclose(restored.to_numpy(), frame.to_numpy()):
                raise RuntimeError(f"Packaged {extension} round-trip failed")
        manager = PlotManager(project.graphs[0], project)
        manager.render()
        for extension in ("png", "jpg", "tiff", "pdf", "svg", "eps"):
            filename = folder / f"graph.{extension}"
            manager.export_image(str(filename), dpi=72)
            if filename.stat().st_size == 0:
                raise RuntimeError(f"Packaged {extension} export is empty")
            if extension in ("png", "jpg", "tiff"):
                with Image.open(filename) as image:
                    image.verify()
