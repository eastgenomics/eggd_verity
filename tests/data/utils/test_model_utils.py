from data.models.reports import BaseMetrics
from data.utils.model_utils import get_metric_models, get_plot_grouping_options


class TestModelUtils:
    def test_get_metric_models(self):
        """
        Verifies that the function returns a dictionary of metric models.
        """
        models = get_metric_models()
        assert isinstance(models, dict)
        assert len(models) > 0

        for name, cls in models.items():
            assert isinstance(name, str)
            assert issubclass(cls, BaseMetrics)

    def test_get_plot_grouping_options(self):
        """
        Verifies that grouping options are returned for Assay, Run, and Sample.
        """
        options = get_plot_grouping_options()
        assert set(options.keys()) == {"Assay", "Run", "Sample"}
        assert isinstance(options["Assay"], list)
        assert "ref_genome" in options["Assay"]
