
import json
# import hashlib
import re
from datetime import datetime

from html2text import html2text

from dojo.models import Finding


class MobSFParser(object):

    def get_scan_types(self):
        return ["MobSF Scan"]

    def get_label_for_scan_types(self, scan_type):
        return "MobSF Scan"

    def get_description_for_scan_types(self, scan_type):
        return "Export a JSON file using the API, api/v1/report_json."

    def get_findings(self, filename, test):
        tree = filename.read()
        try:
            data = json.loads(str(tree, 'utf-8'))
        except:
            data = json.loads(tree)
        find_date = datetime.now()
        dupes = {}
        test_description = ""
        if "app_name" in data:
            test_description = "**Info:**\n"
            if "app_name" in data:
                test_description = "%s  **Name:** %s\n" % (test_description, data["app_name"])

            if "version_name" in data:
                test_description = "%s  **App Version:** %s\n" % (test_description, data["version_name"])

            if "package_name" in data:
                test_description = "%s  **Package Name:** %s\n" % (test_description, data["package_name"])

            if "main_activity" in data:
                test_description = "%s  **Main Activity:** %s\n" % (test_description, data["main_activity"])

            # Not Needed
            # if "app_type" in data:
            #     test_description = "%s  **App Type:** %s\n" % (test_description, data["app_type"])

            # pltfm, sdk, min not in JSON also these are redundant
            # if "pltfm" in data:
            #     test_description = "%s  **Platform:** %s\n" % (test_description, data["pltfm"])
            # if "sdk" in data:
            #     test_description = "%s  **SDK:** %s\n" % (test_description, data["sdk"])
            # if "min" in data:
            #     test_description = "%s  **Min SDK:** %s\n" % (test_description, data["min"])

            if "target_sdk" in data:
                test_description = "%s  **Target SDK:** %s\n" % (test_description, data["target_sdk"])

            if "min_sdk" in data:
                test_description = "%s  **Min SDK:** %s\n" % (test_description, data["min_sdk"])

            if "max_sdk" in data:
                test_description = "%s  **Max SDK:** %s\n" % (test_description, data["max_sdk"])

            test_description = "%s\n**File Information:**\n" % (test_description)

            if "file_name" in data:
                test_description = "%s  **File Name:** %s\n" % (test_description, data["file_name"])

            if "size" in data:
                test_description = "%s  **File Size:** %s\n" % (test_description, data["size"])

            if "md5" in data:
                test_description = "%s  **MD5:** %s\n" % (test_description, data["md5"])

            if "sha1" in data:
                test_description = "%s  **SHA-1:** %s\n" % (test_description, data["sha1"])

            if "sha256" in data:
                test_description = "%s  **SHA-256:** %s\n" % (test_description, data["sha256"])

            # Faulty Code and a lot of URLs
            # if "urls" in data:
            #     curl = ""
            #     for url in data["urls"]:
            #         for curl in url["urls"]:
            #             curl = "%s\n" % (curl)
            #     if curl:
            #         test_description = "%s\n**URL's:**\n %s\n" % (test_description, curl)

            # bin_anal not in JSON
            # if "bin_anal" in data:
            #     test_description = "%s  \n**Binary Analysis:** %s\n" % (test_description, data["bin_anal"])

        test.description = test_description

        mobsf_findings = []
        # Mobile Permissions
        if "permissions" in data:
            # for permission, details in data["permissions"].items():
            if type(data["permissions"]) is list:
                for details in data["permissions"]:
                    mobsf_item = {
                        "category": "Mobile Permissions",
                        "title": details.get("name", ""),
                        "severity": self.getSeverityForPermission(details.get("status")),
                        "description": "**Permission Type:** " + details.get("name", "") + " (" + details.get("status", "") + ")\n\n**Description:** " + details.get("description", "") + "\n\n**Reason:** " + details.get("reason", ""),
                        "file_path": None,
                        "url": None
                    }
                    mobsf_findings.append(mobsf_item)
            else:
                for permission, details in list(data["permissions"].items()):
                    mobsf_item = {
                        "category": "Mobile Permissions",
                        "title": permission,
                        "severity": self.getSeverityForPermission(details.get("status", "")),
                        "description": "**Permission Type:** " + permission + "\n\n**Description:** " + details.get("description", ""),
                        "file_path": None,
                        "url": None
                    }
                    mobsf_findings.append(mobsf_item)

        # Certificate Analysis
        if "certificate_analysis" in data:
            for finding in data["certificate_analysis"]["certificate_findings"]:
                sev = finding[0]
                desc = finding[1]
                title = finding[2]
                mobsf_item = {
                    "category": "Certificate Analysis",
                    "title": title,
                    "severity": sev,
                    "description": desc,
                    "file_path":None,
                    "url": None
                }
                mobsf_findings.append(mobsf_item)

        # Manifest Analysis
        if "manifest_analysis" in data:
            for finding in data["manifest_analysis"]["manifest_findings"]:
                if finding["severity"] == "suppressed":
                    continue
                title = finding["title"]
                severity = finding["severity"]
                desc = finding["description"]
                rule = finding["rule"]
                components = finding["component"]
                mobsf_item = {
                    "category": "Manifest",
                    "title": title,
                    "severity": severity,
                    "description": "**Rule:** " + rule + "\n\n**Description:** " + desc,
                    "file_path": None,
                    "url": None
                }
                mobsf_findings.append(mobsf_item)

        # # insecure_connections not present in JSON
        # # Insecure Connections
        # if "insecure_connections" in data:
        #     for details in data["insecure_connections"]:
        #         insecure_urls = ""
        #         for url in details.split(','):
        #             insecure_urls = insecure_urls + url + "\n"
        #         mobsf_item = {
        #             "category": "Insecure Connections",
        #             "title": "Insecure Connections",
        #             "severity": "Low",
        #             "description": insecure_urls,
        #             "file_path": None
        #         }
        #         mobsf_findings.append(mobsf_item)

        # # Not Required for now
        # # Binary Analysis
        # if "binary_analysis" in data:
        #     if type(data["binary_analysis"]) is list:
        #         for details in data["binary_analysis"]:
        #             for binary_analysis_type in details:
        #                 if "name" != binary_analysis_type:
        #                     mobsf_item = {
        #                         "category": "Binary Analysis",
        #                         "title": details[binary_analysis_type]["description"].split(".")[0],
        #                         "severity": details[binary_analysis_type]["severity"].replace("warning", "low").title(),
        #                         "description": details[binary_analysis_type]["description"],
        #                         "file_path": details["name"],
        #                         "url": None
        #                     }
        #                     mobsf_findings.append(mobsf_item)
        #     else:
        #         for binary_analysis_type, details in list(data["binary_analysis"].items()):
        #             # "Binary makes use of insecure API(s)":{
        #             #     "detailed_desc":"The binary may contain the following insecure API(s) _vsprintf.",
        #             #     "severity":"high",
        #             #     "cvss":6,
        #             #     "cwe":"CWE-676 - Use of Potentially Dangerous Function",
        #             #     "owasp-mobile":"M7: Client Code Quality",
        #             #     "masvs":"MSTG-CODE-8"
        #             # }
        #             mobsf_item = {
        #                 "category": "Binary Analysis",
        #                 "title": details["detailed_desc"],
        #                 "severity": details["severity"].replace("good", "info").title(),
        #                 "description": details["detailed_desc"],
        #                 "file_path": None,
        #                 "url": None
        #             }
        #             mobsf_findings.append(mobsf_item)

        # specific node for Android reports
        if "android_api" in data:
            # "android_insecure_random": {
            #     "files": {
            #         "u/c/a/b/a/c.java": "9",
            #         "kotlinx/coroutines/repackaged/net/bytebuddy/utility/RandomString.java": "3",
            #         ...
            #         "hu/mycompany/vbnmqweq/gateway/msg/Response.java": "13"
            #     },
            #     "metadata": {
            #         "id": "android_insecure_random",
            #         "description": "The App uses an insecure Random Number Generator.",
            #         "type": "Regex",
            #         "pattern": "java\\.util\\.Random;",
            #         "severity": "high",
            #         "input_case": "exact",
            #         "cvss": 7.5,
            #         "cwe": "CWE-330 Use of Insufficiently Random Values",
            #         "owasp-mobile": "M5: Insufficient Cryptography",
            #         "masvs": "MSTG-CRYPTO-6"
            #     }
            # },
            for api, details in list(data["android_api"].items()):
                mobsf_item = {
                    "category": "Android API",
                    "title": details["metadata"]["description"],
                    "severity": details["metadata"]["severity"].replace("warning", "low").title(),
                    "description": "**API:** " + api + "\n\n**Description:** " + details["metadata"]["description"],
                    "file_path": None,
                    "url": None
                }
                mobsf_findings.append(mobsf_item)

        # Firebase URLs
        if "firebase_urls" in data:
            for finding in data["firebase_urls"]:
                url = finding["url"]
                title = "Firebase Database Used"
                if "firebaseio" in url:
                    url_part = url.split("//")[1].split(".")[0]
                    title = "%s: %s" % (title,url_part)
                mobsf_item = {
                    "category": "Firebase Database URL",
                    "title": title,
                    "severity": "info",
                    "description": "Firebase Database Used with URL: " + url,
                    "file_path": None,
                    "url": url
                }
                mobsf_findings.append(mobsf_item)

        ## Secrets
        if "secrets" in data:
            for finding in data["secrets"]:
                title = finding.split(" : ")[0]
                title = title[1:len(title)-1]
                key = finding.split(" : ")[1]
                key = key[1:len(key)-1]
                mobsf_item = {
                    "category": "Secrets",
                    "title": "Hardcoded Secret in " + title,
                    "severity": "high",
                    "description": "**Hardcoded Secret** in " + title + ": " + key,
                    "file_path": None,
                    "url": None
                }
                mobsf_findings.append(mobsf_item)

        # # findings not present in JSON
        # # MobSF Findings
        # if "findings" in data:
        #     for title, finding in list(data["findings"].items()):
        #         description = title
        #         file_path = None
        #         if "path" in finding:
        #             description = description + "\n\n**Files:**\n"
        #             for path in finding["path"]:
        #                 if file_path is None:
        #                     file_path = path
        #                 description = description + " * " + path + "\n"
        #         mobsf_item = {
        #             "category": "Findings",
        #             "title": title,
        #             "severity": finding["level"],
        #             "description": description,
        #             "file_path": file_path,
        #             "url": None
        #         }
        #         mobsf_findings.append(mobsf_item)
        
        for mobsf_finding in mobsf_findings:
            title = mobsf_finding["title"]
            title = re.sub('<[^>]*>', '', title)
            sev = self.getCriticalityRating(mobsf_finding["severity"])
            url = mobsf_finding["url"]
            category = mobsf_finding["category"]
            description = ""
            file_path = None
            description = description + mobsf_finding["description"]
            description = re.sub('<[^>]*>', '', description)
            finding = Finding(
                title=title,
                cwe=919,  # Weaknesses in Mobile Applications
                test=test,
                description=description,
                url=url,
                severity=sev,
                references=None,
                date=find_date,
                static_finding=True,
                dynamic_finding=False,
                nb_occurences=1,
            )
            if mobsf_finding["file_path"]:
                finding.file_path = mobsf_finding["file_path"]

            dupe_key = sev + title + category
            if url is not None:
                dupe_key += url
            if dupe_key in dupes:
                find = dupes[dupe_key]
                if (description is not None) and (description not in find.description):
                    find.description += "\n" + description
                find.nb_occurences += 1
            else:
                finding.description = ("**Category:** " + category + "\n\n%s") % (finding.description)
                dupes[dupe_key] = finding
        return list(dupes.values())

    def getSeverityForPermission(self, status):
        """Convert status for permission detection to severity

        In MobSF there is only 4 know values for permission,
         we map them as this:
        dangerous         => High (Critical?)
        normal            => Info
        signature         => Info (it's positive so... Info)
        signatureOrSystem => Info (it's positive so... Info)
        """
        if "dangerous" == status:
            return "High"
        else:
            return "Info"

    # Criticality rating
    def getCriticalityRating(self, rating):
        criticality = "Info"
        if rating == "warning":
            criticality = "Info"
        else:
            criticality = rating.capitalize()

        return criticality

    def suite_data(self, suites):
        suite_info = ""
        suite_info += suites["name"] + "\n"
        suite_info += "Cipher Strength: " + str(suites["cipherStrength"]) + "\n"
        if "ecdhBits" in suites:
            suite_info += "ecdhBits: " + str(suites["ecdhBits"]) + "\n"
        if "ecdhStrength" in suites:
            suite_info += "ecdhStrength: " + str(suites["ecdhStrength"])
        suite_info += "\n\n"
        return suite_info
