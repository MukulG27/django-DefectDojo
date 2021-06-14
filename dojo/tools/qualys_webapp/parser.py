#!/usr/bin/env python
#
# -*- coding:utf-8 -*-

import base64
import re
import xml.etree.ElementTree
from datetime import datetime
from dojo.models import Endpoint, Finding

try:
    from dojo.settings.settings import QUALYS_WAS_WEAKNESS_IS_VULN
except ImportError:
    # Avoid breaking change
    QUALYS_WAS_WEAKNESS_IS_VULN = False

# Severities are listed under WAS_SCAN_REPORT/APPENDIX/SEVERITY_CATEGORY_LIST
# Since Info findings are not recroded in the Confirmed Vulnerability or
# Potential Vulnerability categories, a severity of 1 is shown as low
# in the portal.
SEVERITY_MATCH = ['Low',
                   'Low',
                   'Medium',
                   'High',
                   'Critical']


def truncate_str(value: str, maxlen: int):
    if len(value) > maxlen:
        return value[:maxlen - 12] + " (truncated)"
    return value


# Parse 'CWE-XXXX' format to strip just the numbers
def get_cwe(cwe):
    cweSearch = re.search("CWE-([0-9]*)", cwe, re.IGNORECASE)
    if cweSearch:
        return cweSearch.group(1)
    else:
        return 0


# Inputs are a list of endpoints and request/response pairs and doctors
# them to fit their respective model structures and the adds them to a
# newly generated Finding
def attach_extras(endpoints, requests, responses, finding, date, qid):
    if finding is None:
        finding = Finding()
        finding.unsaved_req_resp = list()
        finding.unsaved_endpoints = list()
        if date is not None:
            finding.date = date
        finding.vuln_id_from_tool = str(qid)
    else:
        # Finding already exists
        if date is not None and finding.date > date:
            finding.date = date

    for endpoint in endpoints:
        finding.unsaved_endpoints.append(Endpoint.from_uri(endpoint))

    for i in range(0, len(requests)):
        if requests[i] != '' or responses[i] != '':
            finding.unsaved_req_resp.append({"req": requests[i], "resp": responses[i]})

    return finding


# Build a request string by checking for all possible field that could be
# found in the this section of the report
def get_request(request):
    if request is not None:
        header = ''
        header += str(request.findtext('METHOD')) + ': '
        header += str(request.findtext('URL')) + '\n'
        headers = request.find('HEADERS')
        if headers is not None:
            for head in headers.iter('HEADER'):
                header += str(head.findtext('key')) + ': '
                header += str(head.findtext('value')) + '\n'
        return str(header)
    return ''


# Build a response string
def get_response(response):
    if response is not None:
        return decode_tag(response.find('CONTENTS'))
    return ''


# Decode an XML tag with base64 if the tag has base64=true set.
def decode_tag(tag):
    if tag is not None:
        if tag.get("base64") == "true":
            return base64.b64decode(tag.text).decode("utf8", "replace")
        else:
            return tag.text
    return ""


# Retrieve request and response pairs and return a list of requests
# and a list of responses from a single vulnerability
def get_request_response(payloads):
    requests = []
    responses = []
    for payload in payloads.iter('PAYLOAD'):
        requests.append(get_request(payload.find('REQUEST')))
        responses.append(get_response(payload.find('RESPONSE')))
    return [requests, responses]


# Traverse and retreive any information in the VULNERABILITY_LIST
# section of the report. This includes all endpoints and request/response pairs
def get_vulnerabilities(vulnerabilities, is_info=False, is_app_report=False):
    findings = {}
    # Iterate through all vulnerabilites to pull necessary info
    for vuln in vulnerabilities:
        urls = []
        requests = response = ''
        qid = int(vuln.findtext('QID'))
        url = vuln.findtext('URL')
        if url is not None:
            urls.append(str(url))
        access_path = vuln.find('ACCESS_PATH')
        if access_path is not None:
            urls += [url.text for url in access_path.iter('URL')]
        payloads = vuln.find('PAYLOADS')
        if payloads is not None:
            req_resps = get_request_response(payloads)
        else:
            req_resps = [[], []]

        if is_info:
            raw_finding_date = vuln.findtext('LAST_TIME_DETECTED')
        elif is_app_report:
            raw_finding_date = vuln.findtext('FIRST_TIME_DETECTED')
        else:
            raw_finding_date = vuln.findtext('DETECTION_DATE')

        # Qualys uses a non-standard date format.
        if raw_finding_date is not None:
            if raw_finding_date.endswith("GMT"):
                finding_date = datetime.strptime(raw_finding_date, "%d %b %Y %I:%M%p GMT")
            else:
                finding_date = datetime.strptime(raw_finding_date, "%d %b %Y %I:%M%p GMT%z")
        else:
            finding_date = None

        finding = findings.get(qid, None)
        findings[qid] = attach_extras(urls, req_resps[0], req_resps[1], finding, finding_date, qid)
    return findings


# Retrieve information from a single glossary entry such as description,
# severity, title, impact, mitigation, and CWE
def get_glossary_item(glossary, finding, is_info=False, enable_weakness=False):
    title = glossary.findtext('TITLE')
    if title is not None:
        finding.title = str(title)
    severity = glossary.findtext('SEVERITY')
    if severity is not None:
        group = glossary.findtext('GROUP')
        if is_info and (not enable_weakness or group in ("DIAG", "IG")):
            # Scan Diagnostics are always Info.
            finding.severity = "Info"
        else:
            finding.severity = SEVERITY_MATCH[int(severity) - 1]
    description = glossary.findtext('DESCRIPTION')
    if description is not None:
        finding.description = str(description)
    impact = glossary.findtext('IMPACT')
    if impact is not None:
        finding.impact = str(impact)
    solution = glossary.findtext('SOLUTION')
    if solution is not None:
        finding.mitigation = str(solution)
    cwe = glossary.findtext('CWE')
    if cwe is not None:
        finding.cwe = int(get_cwe(str(cwe)))
    return finding


# Retrieve information from a single information gathered entry
def get_info_item(info_gathered, finding):
    data = info_gathered.find('DATA')
    if data is not None:
        finding.description += '\n\n' + decode_tag(data)
    return finding


# Create finding items for all vulnerabilities in the report
def get_items(vulnerabilities, info_gathered, glossary, is_app_report, enable_weakness=False):
    ig_qid_list = [int(ig.findtext('QID')) for ig in info_gathered]
    g_qid_list = [int(g.findtext('QID')) for g in glossary]

    # This dict has findings mapped by QID to remove any duplicates
    findings = {}

    for qid, finding in get_vulnerabilities(vulnerabilities, False, is_app_report).items():
        if qid in g_qid_list:
            index = g_qid_list.index(qid)
            findings[qid] = get_glossary_item(glossary[index], finding, enable_weakness)
    for qid, finding in get_vulnerabilities(info_gathered, True, is_app_report).items():
        if qid in g_qid_list:
            index = g_qid_list.index(qid)
            finding = get_glossary_item(glossary[index], finding, True, enable_weakness)
        if qid in ig_qid_list:
            index = ig_qid_list.index(qid)
            findings[qid] = get_info_item(info_gathered[index], finding)

    return findings


def qualys_webapp_parser(qualys_xml_file, test, enable_weakness=False):
    if qualys_xml_file is None:
        return []

    # supposed to be safe against XEE: https://docs.python.org/3/library/xml.html#xml-vulnerabilities
    tree = xml.etree.ElementTree.parse(qualys_xml_file)
    is_app_report = tree.getroot().tag == 'WAS_WEBAPP_REPORT'

    if is_app_report:
        vulnerabilities = tree.findall('./RESULTS/WEB_APPLICATION/VULNERABILITY_LIST/VULNERABILITY')
        info_gathered = tree.findall('./RESULTS/WEB_APPLICATION/INFORMATION_GATHERED_LIST/INFORMATION_GATHERED')
    else:
        vulnerabilities = tree.findall('./RESULTS/VULNERABILITY_LIST/VULNERABILITY')
        info_gathered = tree.findall('./RESULTS/INFORMATION_GATHERED_LIST/INFORMATION_GATHERED')
    glossary = tree.findall('./GLOSSARY/QID_LIST/QID')

    items = list(get_items(vulnerabilities, info_gathered, glossary, is_app_report, enable_weakness).values())

    return items


class QualysWebAppParser(object):

    def get_scan_types(self):
        return ["Qualys Webapp Scan"]

    def get_label_for_scan_types(self, scan_type):
        return scan_type  # no custom label for now

    def get_description_for_scan_types(self, scan_type):
        return "Qualys WebScan output files can be imported in XML format."

    def get_findings(self, file, test, enable_weakness=QUALYS_WAS_WEAKNESS_IS_VULN):
        return qualys_webapp_parser(file, test, enable_weakness)