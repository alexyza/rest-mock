# -*- coding: utf-8 -*-

"""
Load xlxs file (2010)
"""

from beeprint import pp
# from openpyxl import load_workbook
import pandas as pd
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ExReader(object):
    """
    Reading spreadsheets from a file
    """
    def __init__(self, filename=None):

        super(ExReader, self).__init__()
        if filename is None:
            filename = "/uploads/data/test.xlsx"

        xl = pd.ExcelFile(filename)
        worksheets = {}
        for name in xl.sheet_names:
            worksheets[name] = xl.parse(name)
        self._wb = worksheets
        # self._wb = load_workbook(filename=filename)  # , read_only=True)

    def get_data(self):
        newset = []
        counter = 0
        for name, ws in self._wb.items():
            # print("TEST", name, ws.head())
            counter += 1
            logger.debug("Sheet %s" % name)
            newset.append({
                'name': name,
                'position': counter,  # Note: keep track of sheets order
                'data': self.get_sheet_data(ws),
            })
        pp(newset)

    def read_block(self, data, emit_error=False):

        macro = None
        micro = None
        convention = None
        try:
            macro = data.pop(0).value
            micro = data.pop(0).value
            convention = data.pop(0).value
        except IndexError as e:
            if emit_error:
                raise IndexError("Could not read one of the block elements\n%s"
                                 % str(e))
            return ()

        # Should skip every row which has not a value in the first 3 cells
        if macro is None and micro is None and convention is None:
            if emit_error:
                raise IndexError("All block elements are empty")
            return ()

        return (macro, micro, convention)

    def get_sheet_data(self, ws):

        # print(ws.index, ws.shape, ws.count())
        for i in ws.index:

            # Skip empty lines
            length = ws.loc[i].size
            empty = sum(ws.loc[i].isnull()) == length
            if empty:
                continue

            # Use current row
            row = ws.loc[i]
            print(row)
            exit(1)

        row_num = 0
        languages = []
        terms = []
        latest_micro = None
        latest_macro = "-undefined-"

        for row in ws.rows:
            data = list(row)
            row_num += 1
            last_element = "Unknown"

            # Get the block
            block = self.read_block(data)
            if len(block) == 0:
                if row_num == 1:
                    raise KeyError("Cannot find headers!")
                continue

            # Unpack the block:
            # the first 3 elements removed from data
            macro, micro, convention = block

            if row_num > 1:
                # Macro update
                if macro is not None and macro.strip() != '':
                    latest_macro = macro.strip().lower()
                if latest_macro is None:
                    raise KeyError("Empty macro inside '%s' sheet" % ws.title)
                # Micro update
                if micro is not None and micro.strip() != '':
                    latest_micro = micro.strip().lower()
                if latest_micro is None:
                    latest_micro = latest_macro

            cell_num = -1

            from collections import OrderedDict
            term = OrderedDict({
                'term': convention,  # Note: convention should not be shown
                'macro': latest_macro,
                'micro': latest_micro,
                'sheet': ws.title.strip().lower()
            })
            # print("TERM", term)

            for element in data:
                cell_num += 1
                if element.value is None:
                    if row_num == 1:
                        if last_element is None and element.value is not None:
                            raise KeyError("Missing language column name")
# Warning: we need to know how many languages are expected!
                    if cell_num > 6 and last_element is None:
                        break
                else:
                    element.value = element.value[:].strip()

                # First row (header) tells you which languages
                # Store languages names from cell 4 on
                if row_num == 1 and element.value is not None:
                    languages.append(element.value)
                else:
                    try:
                        language = languages[cell_num]
                        term[language] = element.value
                    except IndexError:
                        pass

                # Keep track of last element
                last_element = element.value

            # Add last row/term
            if row_num > 1:
                # print("TERM", term)
                terms.append(dict(term))
                # terms.append(list(term.values()))

            # ## JUST FOR DEBUG
            # if row_num > 2:
            #     break

            # # Note: this works with lists, not dictionary...
            # if False:
            #     from tabulate import tabulate
            #     table = tabulate(
            #         terms,  # headers=term.keys(),
            #         tablefmt="fancy_grid")
            #     print(table)
            #     break

        return terms


if __name__ == '__main__':
    xls = ExReader()
    print(xls.get_data())
