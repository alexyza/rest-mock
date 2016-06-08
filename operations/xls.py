# -*- coding: utf-8 -*-

"""
Load xlxs file (2010)
"""

from openpyxl import load_workbook


class ExReader(object):
    """
    Reading spreadsheets from a file
    """
    def __init__(self, filename=None):

        super(ExReader, self).__init__()

        if filename is None:
            filename = "/Users/paulie/Downloads/test_baroque.xlsx"

        wb = load_workbook(filename=filename, read_only=True)
        # print(wb)
        # print(wb.worksheets)
        """
[<ReadOnlyWorksheet "Plan">, <ReadOnlyWorksheet "fête">, <ReadOnlyWorksheet "dispositif">, <ReadOnlyWorksheet "perfomance">, <ReadOnlyWorksheet "expérience">, <ReadOnlyWorksheet "Fins">, <ReadOnlyWorksheet "a classer">, <ReadOnlyWorksheet "exclus">]
        """

        ## ALL
        # for ws in wb.worksheets:
        #     self.get_sheet_data(ws)

        ## SINGLE
        # self.get_sheet_data(wb['perfomance'])
        self.get_sheet_data(wb['dispositif'])

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

        row_num = 0
        languages = []
        terms = []
        latest_macro = latest_micro = "-undefined-"

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
                if macro is not None and macro.strip() != '':
                    latest_macro = macro
                if micro is not None and micro.strip() != '':
                    latest_micro = micro

            cell_num = -1

            from collections import OrderedDict
            term = OrderedDict({
                'term': convention,
                'macro': latest_macro,
                'micro': latest_micro,
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
                print("TERM", term)
                terms.append(list(term.values()))

            if row_num > 15:
                from tabulate import tabulate
                table = tabulate(
                    terms,
                    # headers=term.keys(),
                    tablefmt="fancy_grid")
                print(table)
                # print(terms)
                break

if __name__ == '__main__':
    ExReader()