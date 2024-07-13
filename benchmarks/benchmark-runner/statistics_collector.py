from collections import OrderedDict
from copy import deepcopy
import json

class StatisticsCollector:
    def __init__(self, title="Statistics"):
        self.title = title
        self.statistics = OrderedDict()

    def add_statistic(self, category, subcategory, value, as_percentage=False):
        if category not in self.statistics:
            self.statistics[category] = OrderedDict()
        self.statistics[category][subcategory] = {'value': value, 'as_percentage': as_percentage}

    def set_title(self, title):
        self.title = title

    def merge(self, other):
        self._recursive_update(self.statistics, other.statistics)

    def _recursive_update(self, d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._recursive_update(d[k], v)
            else:
                d[k] = v

    def _format_value(self, value, as_percentage):
        if as_percentage:
            return f"{value:,.2%}"
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def to_str(self, min_width=50, space_filler='.'):
        space_inner = '  '
        space_outer = ''
        
        max_cat_len = max((len(cat) for cat in self.statistics), default=0)
        max_subcat_len = max((len(subcat) for cat in self.statistics.values() for subcat in cat), default=0) + len(space_outer) + len(space_inner)
        max_val_len = max((len(self._format_value(val['value'], val['as_percentage'])) for cat in self.statistics.values() for val in cat.values()), default=0) + len(space_outer) + len(space_inner)
        max_width = max(max(max_subcat_len + max_val_len, max_cat_len) + 10, min_width)
        
        sep_line = f"{'':#^{max_width}}"
        
        output = [
            sep_line,
            f"{self.title:^{max_width}}",
            sep_line,
        ]
        
        for category, subcategories in self.statistics.items():
            output.append(f"{f' {category} ':~^{max_width}}")

            for subcategory, value in subcategories.items():
                formatted_value = self._format_value(value['value'], value['as_percentage'])
                output.append(f"{f'{space_outer}{subcategory}{space_inner}':{space_filler}<{max_subcat_len}}{f'{space_inner}{formatted_value}{space_outer}':{space_filler}>{max_width-max_subcat_len}}")

        output.append(sep_line)
        return '\n'.join(output)

    def to_json(self):
        d = deepcopy(self.statistics)
        
        for category, sub_categories in d.items():
            for sub_category, v in sub_categories.items():
                sub_categories[sub_category] = v['value']

        return json.dumps(d, indent=4)

    def __str__(self):
        return self.to_str()
