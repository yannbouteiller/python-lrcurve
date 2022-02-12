# From https://github.com/lvwerra/jupyterplot

__all__ = ['ProgressPlot']

# Cell
import IPython
import matplotlib.pyplot as plt

try:
    from portilooplot.plot_learning_curve import PlotLearningCurve
except:
    from portilooplot.plot_learning_curve import PlotLearningCurve
# so sorry for this hack :( the first import goes through
# the lrcurve __init__ which triggers a keras/tf import which should
# be avoided. the second import bypasses this and imports directly
# from the plot_learning_curve module not requiring keras/tf.


class ProgressPlot(PlotLearningCurve):
    """
    Real-time progress plots for Jupyter notebooks.
    Parameters
    ----------
    plot_names : list of str, optional, default: ``['plot']``
        Labels for plots. Length also determines number of plots.
    line_names: list of str, optional, default: ``['line-1']``
        Labels for lines. Length also determines number of lines per plot.
    line_colors: list of str, optional, default: ``None``
        Color cycle for lines in hex format. If ``None``
        the standard matplotlib color cycle is used.
    x_lim: list, optional, default: ``[None, None]``
        List with ``[x_min, x_max]``. If value is ``None`` the
        axes on that side is dynamically adjusted.
    y_lim: list, optional, default: ``[None, None]``
        List with ``[y_min, y_max]``. If value is ``None`` the
        axes on that side is dynamically adjusted.
    x_label='iteration': str, optional, default: ``'iteration'``
        Label for the x-axis. Default is ``'iteration'``
    x_iterator: boolean, optional, default: ``True``
        If flag is ``True`` an internal iterator is used as
        x values for the plot. If ``False`` the update function
        requires an x value.
    height: int, optional, default: ``None``
        The height in pixels of the plot (default None). The default
        behavior is to use 200px per facet and an additional 90px for
        the x-axis and legend.
    width: int, optional, default: ``600``
        The width in pixels of the plot (default 600).
    display_fn: callable, optional, default: ``IPython.display.display``
        To display HTML or JavaScript in a notebook with an IPython
        backend, `IPython.display.display` is called. The called function
        can be overwritten by setting this argument (mostly useful for
        internal testing).
    debug: boolean, optional, default: ``False``
        Depending on the notebook, a JavaScript evaluation does not provide
        a stack trace in the developer console. Setting this to `true` works
        around that by injecting `<script>` tags instead.
    """

    def __init__(
        self,
        plot_names=["plot"],
        line_names=["line-1"],
        line_colors=None,
        x_lim=[None, None],
        y_lim=[None, None],
        x_label="iteration",
        x_iterator=True,
        height=None,
        width=600,
        display_fn=IPython.display.display,
        debug=False,
        max_window_len=100
    ):

        self.width = width
        self.height = height
        self.display_fn = display_fn
        self.debug = debug
        self._plot_is_setup = False
        self._plots = plot_names
        self.line_names = line_names
        self.line_colors = line_colors
        self.x_lim = x_lim
        self.y_lim = y_lim
        self.x_label = x_label
        self.iterator = 0
        self.max_window_len = max_window_len

        if isinstance(y_lim[0], list):
            if len(y_lim)==len(plot_names):
                self.y_lim = y_lim
            else:
                raise ValueError(f"Unequal number of y limits and plots ({len(y_lim)} and {len(plot_names)}).")
        else:
            self.y_lim = [y_lim] * len(plot_names)

        if not line_colors:
            line_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

        # setup color cycle from list of line colors
        self.line_colors = [
            line_colors[i % len(line_colors)] for i in range(len(line_names))
        ]

        if x_iterator:
            self.update = self._update_with_iter
        else:
            self.update = self._update_with_x

        self._setup_plot()

    def update_with_datapoints(self, datapoints):
        for datapoint in datapoints:
            datapoint = self._parse_y(datapoint)
            self.append(self.iterator, datapoint)
            self.iterator += 1
        self.draw()

    def _update_with_iter(self, y):
        """
        Update plot with internal iterator.
        Parameters
        ----------
        y: float, list, dict
            y-value of data update. If single plot with
            single line a float can be passed. Otherwise
            a list of lists for each plot and line or a
            dict of dicts with the plot and line names must
            be passed.
        """
        self._update_with_x(self.iterator, y)
        self.iterator += 1

    def _update_with_x(self, x, y):
        """
        Update plot with external x-values.
        Parameters
        ----------
        x: int, float
            x-value of data update.
        y: float, list, dict
            y-value of data update. If single plot with
            single line a float can be passed. Otherwise
            a list of lists for each plot and line or a
            dict of dicts with the plot and line names must
            be passed.
        """
        y = self._parse_y(y)
        self.append(x, y)
        self.draw()

    def _parse_y(self, y):
        """Parse y-data to dict for js."""
        if isinstance(y, dict):
            return y
        elif isinstance(y, list):
            return self._y_list_to_dict(y)
        elif isinstance(y, (int, float)):
            return self._y_scalar_to_dict(y)
        else:
            raise ValueError(
                "Not supported data type for update. Should be one of dict/list/float."
            )

    def _y_list_to_dict(self, y):
        """Parse y-data in list to dict for js."""
        if not (len(y) == len(self._plots)):
            raise ValueError("Number of plot updates not equal to number of plots!")
        if not all(isinstance(yi, list) for yi in y):
            raise ValueError("Line updates not of type list!")
        if not all(len(yi) == len(self.line_names) for yi in y):
            raise ValueError(
                "Number of line update values not equal to number of lines!"
            )

        y_dict = {
            plot: {line: y_ij for line, y_ij in zip(self.line_names, y_i)}
            for plot, y_i in zip(self._plots, y)
        }
        return y_dict

    def _y_scalar_to_dict(self, y):
        """Parse y-data int/or float to dict for js."""
        if not (len(self._plots) == 1 and len(self.line_names) == 1):
            raise ValueError(
                "Can only update with int/float with one plot and one line."
            )

        y_dict = {self._plots[0]: {self.line_names[0]: y}}
        return y_dict

    def _setup_plot(self):
        """Setup progress plot by calling initializing PlotLearningCurve class."""

        line_config = {
            name: {"name": name, "color": color}
            for name, color in zip(self.line_names, self.line_colors)
        }
        facet_config = {
            name: {"name": name, "limit": y_lim} for name, y_lim in zip(self._plots, self.y_lim)
        }
        xaxis_config = {"name": self.x_label, "limit": self.x_lim}

        super().__init__(
            height=self.height,
            width=self.width,
            line_config=line_config,
            facet_config=facet_config,
            xaxis_config=xaxis_config,
            display_fn=self.display_fn,
            debug=self.debug,
            max_window_len=self.max_window_len
        )