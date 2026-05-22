from textual_plotext import PlotextPlot


class GraphWidget(PlotextPlot):
    def __init__(self, graph_title: str,
                 data_x_label: str,
                 data_y_label: str,
                 series_1_label: str,
                 series_2_label: str,
                 series_x1: list = [],
                 series_x1_limit: int | float | None = None,
                 series_y1: list = [],
                 series_y1_limit: float | int | None = None,
                 series_x2: list = [],
                 series_x2_limit: int | float | None = None,
                 series_y2: list = [],
                 series_y2_limit: float | int | None = None,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.graph_title = graph_title
        self.data_x_label = data_x_label
        self.series_x1 = series_x1
        self.series_x1_limit = series_x1_limit
        self.series_1_label = series_1_label
        self.data_y_label = data_y_label
        self.series_y1 = series_y1
        self.series_y1_limit = series_y1_limit
        self.series_x2 = series_x2
        self.series_x2_limit = series_x2_limit
        self.series_2_label = series_2_label
        self.series_y2 = series_y2
        self.series_y2_limit = series_y2_limit
        self.plt.title(graph_title)
        self.plt.xlabel(data_x_label)
        self.plt.ylabel(data_y_label)

    def set_data(self, series_x1: list, series_x1_limit: int | float | None, series_y1: list, series_y1_limit: float | int | None, series_x2: list = [], series_x2_limit: int | float | None = None, series_y2: list = [], series_y2_limit: float | int | None = None) -> None:
        self.series_x1 = series_x1
        self.series_x1_limit = series_x1_limit
        self.series_y1 = series_y1
        self.series_y1_limit = series_y1_limit
        self.series_x2 = series_x2
        self.series_x2_limit = series_x2_limit
        self.series_y2 = series_y2
        self.series_y2_limit = series_y2_limit
        self.render_graph()

    def clear_data(self) -> None:
        self.plt.clear_data()
        self.refresh()

    def render_graph(self) -> None:

        self.plt.clear_data()
        self.plt.date_form(input_form="d/m/Y H:M:S Z", output_form="H:M")
        self.plt.plot(self.series_x1,
                      self.series_y1, marker="braille", label=self.series_1_label)

        if self.series_x2 != [] and self.series_y2 != []:
            self.plt.plot(self.series_x2,
                          self.series_y2, marker="braille", label=self.series_2_label)

        self.plt.xlim(right=self.series_x1_limit)
        self.plt.ylim(0, self.series_y1_limit)
        self.plt.plotsize(self.size.width, self.size.height)

        self.refresh()
