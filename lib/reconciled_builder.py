"""Take the unreconciled dataframe and build the reconciled and explanations
dataframes.
"""

import re
from functools import reduce
from collections import Counter, namedtuple
from itertools import combinations
from fuzzywuzzy import fuzz
import lib.util as util


class ReconciledBuilder:
    """Build the reconciled dataframe from the unreconciled dataframe."""

    place_holders = ['placeholder']  # Replace placeholders with empty string

    ExactScore = namedtuple('ExactScore', 'value count')
    FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
    FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')

    unwanted_columns = ['subject_data', 'subject_retired', 'subject_subjectId']

    total_plurals = {'records': 'records', 'All': 'All', 'are': 'are'}
    total_singulars = {'records': 'record', 'All': 'The', 'are': 'is'}
    blank_plurals = {'blanks': 'blanks'}
    blank_singulars = {'blanks': 'blank'}

    def __init__(self, args, unreconciled_df):
        self.args = args
        self.unreconciled_df = unreconciled_df

    def build(self):
        """This is the function called by external modules."""

        # Aggregate columns based on each column's type keyed by column name
        method_for_select_columns = {col: self.best_select_value
                                     for col in self.unreconciled_df.columns
                                     if re.match(util.SELECT_COLUMN_PATTERN,
                                                 col)}
        method_for_text_columns = {col: self.best_text_value
                                   for col in self.unreconciled_df.columns
                                   if re.match(util.TEXT_COLUMN_PATTERN, col)}
        method_for_subject_columns = {col: self.all_are_identical
                                      for col in self.unreconciled_df.columns
                                      if col.startswith('subject_')
                                      and col != util.GROUP_BY}

        best_value_methods = method_for_select_columns.copy()
        best_value_methods.update(method_for_text_columns)
        best_value_methods.update(method_for_subject_columns)

        best_value_methods = {k: v for k, v in best_value_methods.items()
                              if k not in self.unwanted_columns}  # Remove junk

        # Aggregate using the per column functions setup above
        reconciled_df = self.unreconciled_df.fillna('').groupby(util.GROUP_BY)
        reconciled_df = reconciled_df.aggregate(best_value_methods)

        # Split the combined reconciled value & explanation tuple into columns
        combined = list(method_for_text_columns.keys()) + \
            list(method_for_select_columns.keys())
        for col in combined:
            reconciled_df[col + '_explanation'] = reconciled_df[col].apply(
                lambda t: t[0])
            reconciled_df[col] = reconciled_df[col].apply(lambda t: t[1])

        reconciled_df = reconciled_df.reindex_axis(
            sorted(reconciled_df.columns), axis=1)

        explanations_df = \
            reconciled_df.loc[:, [col
                                  for col in reconciled_df.columns
                                  if col.endswith('_explanation')]]
        explanations_cols = {col: col.replace('_explanation', '')
                             for col in explanations_df.columns}
        explanations_df.rename(columns=explanations_cols, inplace=True)

        reconciled_df.drop([col for col in reconciled_df.columns
                            if col.endswith('_explanation')],
                           axis=1, inplace=True)

        return reconciled_df, explanations_df

    @staticmethod
    def normalize_text(group):
        """Collapse space into one space and EOLs into one EOL."""

        return ['\n'.join([' '.join(ln.split()) for ln in str(g).splitlines()])
                for g in group]

    def top_partial_ratio(self, values):
        """Return the best partial ratio match from fuzzywuzzy module."""

        scores = []
        for combo in combinations(values, 2):
            score = fuzz.partial_ratio(combo[0], combo[1])
            value = combo[0] if len(combo[0]) >= len(combo[1]) else combo[1]
            scores.append(self.FuzzyRatioScore(score, value))
        scores = sorted(scores,
                        reverse=True,
                        key=lambda s: (s.score, len(s.value)))
        return scores[0]

    def top_token_set_ratio(self, values):
        """Return the best token set ratio match from fuzzywuzzy module."""

        scores = []
        for combo in combinations(values, 2):
            score = fuzz.token_set_ratio(combo[0], combo[1])
            tokens_0 = len(combo[0].split())
            tokens_1 = len(combo[1].split())
            if tokens_0 > tokens_1:
                value = combo[0]
                tokens = tokens_0
            elif tokens_0 < tokens_1:
                value = combo[1]
                tokens = tokens_1
            else:
                tokens = tokens_0
                value = combo[1]
                if len(combo[0]) <= len(combo[1]):
                    value = combo[0]

            scores.append(self.FuzzySetScore(score, value, tokens))
        ordered = sorted(
            scores,
            reverse=True,
            key=lambda s: (s.score, s.tokens, 1000000 - len(s.value)))
        return ordered[0]

    @staticmethod
    def all_are_identical(group):
        """Handle a group where all of the items are identical."""

        values = [g for g in group]
        return values[0]

    @staticmethod
    def explain_values(values, filled):
        """Get group values used in the best choice explanations."""

        record_count = len(values)
        blank_count = record_count - reduce(
            (lambda x, y: x + y.count), filled, 0)
        return record_count, blank_count

    def format_explanation(self, form, record_count=None, blank_count=None,
                           match_count=None, match_type=None, score=None):
        """Build an explanation for the group's best choice."""

        std_words = dict(record_count=record_count,
                         blank_count=blank_count,
                         match_count=match_count,
                         match_type=match_type,
                         score=score)

        total_words = self.total_plurals.copy()
        if record_count == 1:
            total_words = self.total_singulars.copy()

        blank_words = self.blank_plurals.copy()
        if blank_count == 1:
            blank_words = self.blank_singulars.copy()

        words = dict(list(total_words.items()) +
                     list(blank_words.items()) +
                     list(std_words.items()))
        return form.format(**words)

    def explain_all_blank(self, values):
        """Explain case where all values in the group are blank."""

        record_count = len(values)
        return (self.format_explanation(
            '{All} {record_count} {records} {are} blank',
            record_count=record_count), '')

    def explain_one_transcript(self, value, values, filled):
        """Explain the case where one value in the group is filled and all
        others are blank.
        """

        record_count, _ = self.explain_values(values, filled)
        form = 'Only 1 transcript in {record_count} {records}'
        return (self.format_explanation(form,
                                        record_count=record_count),
                value)

    def explain_no_match(self, values, filled, match_type):
        """Explain when we are unable to match any value in the group."""

        record_count, blank_count = self.explain_values(values, filled)
        form = ('No {match_type} match on {record_count} {records} '
                'with {blank_count} {blanks}')
        return (self.format_explanation(form,
                                        record_count=record_count,
                                        blank_count=blank_count,
                                        match_type=match_type), '')

    def explain_exact_match(self, value, values, filled, match_type):
        """Explain when we have an exact match between items in the group."""

        record_count, blank_count = self.explain_values(values, filled)
        form = ('{match_type} match, {match_count} of {record_count} '
                '{records} with {blank_count} {blanks}')
        return (self.format_explanation(form,
                                        record_count=record_count,
                                        match_count=filled[0].count,
                                        blank_count=blank_count,
                                        match_type=match_type), value)

    def explain_fuzzy_match(self, value, values, filled, score, match_type):
        """Explain the case where we do a fuzzy match on the group."""

        record_count, blank_count = self.explain_values(values, filled)
        form = ('{match_type} match on {record_count} {records} '
                'with {blank_count} {blanks}, score={score}')
        return (self.format_explanation(form,
                                        record_count=record_count,
                                        blank_count=blank_count,
                                        match_type=match_type,
                                        score=score), value)

    def only_filled_values(self, values):
        """Get the items in the group where they are filled and sort by frequency.
        """

        return [self.ExactScore(cnt[0], cnt[1])
                for cnt in Counter([v for v in values if v]).most_common()]

    def best_select_value(self, group):
        """Handle the case where the group is for a drop-down select list."""

        values = [str(g) if str(g).lower() not in self.place_holders else ''
                  for g in group]
        filled = self.only_filled_values(values)

        if not filled:
            return self.explain_all_blank(values)

        if filled[0].count > 1:
            return self.explain_exact_match(filled[0].value,
                                            values,
                                            filled,
                                            'Exact')

        if len(filled) == 1:
            return self.explain_one_transcript(filled[0].value, values, filled)

        return self.explain_no_match(values, filled, 'select')

    def best_text_value(self, group):
        """Handle the case where the group is a free-form text field."""

        values = self.normalize_text(group)
        filled = self.only_filled_values(values)

        if not filled:
            return self.explain_all_blank(values)

        if filled[0].count > 1:
            return self.explain_exact_match(filled[0].value,
                                            values,
                                            filled,
                                            'Normalized exact')

        if len(filled) == 1:
            return self.explain_one_transcript(filled[0].value, values, filled)

        # Check for simple in-place fuzzy matches
        top = self.top_partial_ratio(values)
        if top.score >= self.args.fuzzy_ratio_threshold:
            return self.explain_fuzzy_match(top.value,
                                            values,
                                            filled,
                                            top.score,
                                            'Partial ratio')

        # Now look for the best token match
        top = self.top_token_set_ratio(values)
        if top.score >= self.args.fuzzy_set_threshold:
            return self.explain_fuzzy_match(top.value,
                                            values,
                                            filled,
                                            top.score,
                                            'Token set ratio')

        return self.explain_no_match(values, filled, 'text')
