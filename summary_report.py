import re
import xml.etree.ElementTree as et
from datetime import datetime
from collections import Counter, namedtuple
import utils


HTML_TEMPLATE = '''
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title />
    <style>
      header h1 { text-align: center; }
      header div { width: 360px; margin-bottom: 4px; }
      header div label { text-align: right; display: inline-block; width: 200px; }
      header div span { float: right; }
      section { margin-top: 2em; margin-bottom: 1em; }
      th { padding: 2px 4px; }
      #stats thead tr:nth-child(1) th:nth-child(2) { background: lightgray; }
      #stats thead tr:nth-child(2) th { text-decoration: underline; }
      #stats thead tr:nth-child(2) th:nth-child(1) { text-align: left; }
      #stats thead tr:nth-child(2) th:nth-child(2) { text-align: left; }
      #stats tr td:nth-child(3), #stats tr th:nth-child(3) { text-align: right; }
      #stats tr td:nth-child(4), #stats tr th:nth-child(4) { text-align: right; }
      #stats tr td:nth-child(5), #stats tr th:nth-child(5) { text-align: right; }
      #stats tr td:nth-child(6), #stats tr th:nth-child(6) { text-align: right; }
      #stats tr td:nth-child(7), #stats tr th:nth-child(7) { text-align: right; }
      #stats tr td:nth-child(8), #stats tr th:nth-child(8) { text-align: right; }
      #stats tr td:nth-child(1){ padding-left: 4px; }
      #stats tr td:nth-child(2){ padding-left: 4px; }
      #stats tr td:nth-child(3){ padding-right: 12px; }
      #stats tr td:nth-child(4){ padding-right: 12px; }
      #stats tr td:nth-child(5){ padding-right: 12px; }
      #stats tr td:nth-child(6){ padding-right: 12px; }
      #stats tr td:nth-child(7){ padding-right: 12px; }
      #stats tr td:nth-child(8){ padding-right: 12px; }
      #problems th { text-align: left; text-decoration: underline; }
      #problems td { padding-left: 4px; }
    </style>
  </head>
  <body>
    <header>
      <h1 id="title" />
      <div><label>Date:</label><span id="date" /></div>
      <div><label>Number of Subjects:</label><span id="subjects" /></div>
      <div><label>Number of Transcripts:</label><span id="transcripts" /></div>
      <div><label>Transcripts per Subject:</label><span id="ratio" /></div>
    </header>
    <section id="stats">
      <h2>Reconciled Data</h2>
      <table>
        <thead>
          <tr>
            <th colspan="2"></th>
            <th colspan="5">Reconciled</th>
            <th colspan="1"></th>
          </tr>
          <tr>
            <th>Field</th>
            <th>Type</th>
            <th>Exact Matches</th>
            <th>Fuzzy Matches</th>
            <th>All Blank</th>
            <th>One Transcript</th>
            <th>Total</th>
            <th>No Matches</th>
          </tr>
        </thead>
        <tbody />
      </table>
    </section>
    <section id="problems">
      <h2>Problem Records</h2>
      <table>
        <thead />
        <tbody />
      </table>
    </section>
  </body>
</html>
'''


def create_summary_report(unreconciled_df, reconciled_df, explanations_df, args):
    html = et.fromstring(HTML_TEMPLATE)
    workflow_name = unreconciled_df.loc[0, 'workflow_name'] if 'workflow_name' in unreconciled_df.columns else ''
    workflow_name = re.sub(r'^[^_]*_', '', workflow_name)

    html.find('.head/title').text = 'Summary of {}'.format(args.workflow_id)

    html.find(".//h1[@id='title']").text = 'Summary of "{}" ({})'.format(workflow_name, args.workflow_id)
    html.find(".//span[@id='date']").text = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M')
    html.find(".//span[@id='subjects']").text = '{:,}'.format(reconciled_df.shape[0])
    html.find(".//span[@id='transcripts']").text = '{:,}'.format(unreconciled_df.shape[0])
    html.find(".//span[@id='ratio']").text = '{:.2f}'.format(unreconciled_df.shape[0] / reconciled_df.shape[0])

    # These depend on the patterns put into explanations_df FIXME
    no_match_pattern = r'^No (?:select|text) match on'
    exact_match_pattern = r'^(?:Exact|Normalized exact) match'
    fuzz_match_pattern = r'^(?:Partial|Token set) ratio match'
    all_blank_pattern = r'^(?:All|The) \d+ record'
    onesies_pattern = r'^Only 1 transcript in'

    tbody = html.find(".//section[@id='stats']/table/tbody")
    for col in [c for c in explanations_df.columns]:
        name = utils.format_name(col)
        col_type = 'select' if re.match(utils.SELECT_COLUMN_PATTERN, col) else 'text'
        num_no_match = explanations_df[explanations_df[col].str.contains(no_match_pattern)].shape[0]
        num_exact_match = explanations_df[explanations_df[col].str.contains(exact_match_pattern)].shape[0]
        num_fuzzy_match = explanations_df[explanations_df[col].str.contains(fuzz_match_pattern)].shape[0]
        num_all_blank = explanations_df[explanations_df[col].str.contains(all_blank_pattern)].shape[0]
        num_onesies = explanations_df[explanations_df[col].str.contains(onesies_pattern)].shape[0]
        num_reconciled = explanations_df.shape[0] - num_no_match

        tr = et.Element('tr')

        td = et.Element('td')
        td.text = name
        tr.append(td)

        td = et.Element('td')
        td.text = col_type
        tr.append(td)

        td = et.Element('td')
        td.text = '{:,}'.format(num_exact_match)
        tr.append(td)

        td = et.Element('td')
        td.text = '{:,}'.format(num_fuzzy_match) if col_type == 'text' else ''
        tr.append(td)

        td = et.Element('td')
        td.text = '{:,}'.format(num_all_blank)
        tr.append(td)

        td = et.Element('td')
        td.text = '{:,}'.format(num_onesies)
        tr.append(td)

        td = et.Element('td')
        td.text = '{:,}'.format(num_reconciled)
        tr.append(td)

        td = et.Element('td')
        td.text = '{:,}'.format(num_no_match)
        tr.append(td)

        tbody.append(tr)

    thead = html.find(".//section[@id='problems']/table/thead")
    tr = et.Element('tr')
    th = et.Element('th')
    th.text = explanations_df.index.name
    tr.append(th)
    for col in explanations_df.columns:
        th = et.Element('th')
        th.text = utils.format_name(col)
        tr.append(th)
    thead.append(tr)

    tbody = html.find(".//section[@id='problems']/table/tbody")
    pattern = '|'.join([no_match_pattern, onesies_pattern])
    for subject_id, cols in explanations_df.iterrows():
        tr = et.Element('tr')
        td = et.Element('td')
        td.text = str(subject_id)
        tr.append(td)
        keep = False
        for col in cols:
            td = et.Element('td')
            if re.search(pattern, col):
                keep = True
                td.text = col
            tr.append(td)
        if keep:
            tbody.append(tr)

    with open(args.summary, 'wb') as out_file:
        out_file.write('<!DOCTYPE html>\n'.encode())
        out_file.write(et.tostring(html))
