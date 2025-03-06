import os
import sys
import json
import logging
import requests
import ssl
import time
import http.client
import urllib.parse
import xml.etree.ElementTree as ET
from logging.handlers import TimedRotatingFileHandler
from requests.auth import HTTPBasicAuth
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QHeaderView, QFrame
)

# Define the log file path
LOG_DIR = os.path.expanduser("~/.library_checkin")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "library_checkin.log")

def init_logging():
    logging.basicConfig(
        level=logging.DEBUG,  # Set the desired logging level
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
        handlers=[
            TimedRotatingFileHandler(
                LOG_FILE,  # File path
                when="midnight",  # Rotate at midnight
                interval=1,  # Rotate every day
                backupCount=14,  # Keep logs for 14 days
            ),
            logging.StreamHandler()  # Also log to the console
        ]
    )
    logging.info("Logging initialized. Log file: %s", LOG_FILE)

# Call logging initialization early in the script
init_logging()

# Get the path to the directory containing the executable or script
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)

def get_config_path():
    """Get the path to config.json, prioritizing external file over bundled one"""
    # First, try to find config.json in the same directory as the executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        exe_dir = os.path.dirname(sys.executable)
        external_config = os.path.join(exe_dir, "config.json")
        if os.path.exists(external_config):
            logging.info("Using external config.json from executable directory")
            return external_config
    
    # If not found or running from source, try current directory
    current_dir_config = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(current_dir_config):
        logging.info("Using config.json from current directory")
        return current_dir_config
    
    # Fall back to bundled config
    logging.info("Using bundled config.json")
    return resource_path("config.json")

# Load configuration from config.json
try:
    config_path = get_config_path()
    with open(config_path, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"Error: 'config.json' not found in the application directory.")
    logging.error("config.json not found at: %s", config_path)
    sys.exit(1)
except json.JSONDecodeError:
    print(f"Error: 'config.json' contains invalid JSON.")
    logging.error("Invalid JSON in config.json at: %s", config_path)
    sys.exit(1)


class BookCheckInApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Book Check-In System")
        self.setGeometry(200, 200, 800, 600)
        self.setWindowIcon(QIcon(resource_path("app_icon.ico")))
        self.token_info = None  # To store token and expiry time

        # Initialize attributes with default values
        self.barcode_input = None
        self.process_button = None
        self.status_label = None
        self.results_table = None
        self.row_count_label = None

        self.initUI()  # Build all UI components here

    def initUI(self):
        """
        Builds and lays out all UI elements in a refined, more modern style.
        """
        # -- MAIN CONTAINER --
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # -- HEADER WIDGET WITH SUBTLE BACKGROUND --
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_widget.setAutoFillBackground(True)

        # Light gray background for the header
        header_palette = header_widget.palette()
        header_palette.setColor(QPalette.Window, QColor("#f2f2f2"))
        header_widget.setPalette(header_palette)

        # Title Label
        header_label = QLabel("Check-In Books", self)
        header_label.setFont(QFont("Arial", 22, QFont.Bold))
        header_layout.addWidget(header_label)

        # Subheader Label
        sub_header = QLabel(
            "Scan the barcode of each returning book. "
            "Once all books are scanned, review the table below for any errors."
        )
        sub_header.setFont(QFont("Arial", 12))
        sub_header.setWordWrap(True)
        header_layout.addWidget(sub_header)

        main_layout.addWidget(header_widget)

        # -- SEPARATOR LINE --
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.HLine)
        separator_line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator_line)

        # -- SCANNING FRAME (Barcode + Button) --
        scanning_frame = QFrame()
        scanning_layout = QHBoxLayout(scanning_frame)
        scanning_layout.setSpacing(8)
        scanning_layout.setContentsMargins(0, 0, 0, 0)

        # Icon to the left of the barcode label
        icon_label = QLabel()
        try:
            icon_pixmap = QPixmap(resource_path("barcode_icon.png"))
            if icon_pixmap.isNull():  # Check if the image could not be loaded
                raise FileNotFoundError("Icon file 'barcode_icon.png' not found or invalid.")
            icon_pixmap = icon_pixmap.scaled(24, 24, Qt.KeepAspectRatio)
            icon_label.setPixmap(icon_pixmap)
            scanning_layout.addWidget(icon_label)
        except FileNotFoundError as e:
            logging.warning(f"Icon loading failed: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while loading icon: {e}")

        # Barcode Label
        barcode_label = QLabel("Barcode:")
        barcode_label.setFont(QFont("Arial", 12))
        scanning_layout.addWidget(barcode_label)

        # Barcode Input
        self.barcode_input = QLineEdit()
        self.barcode_input.setFont(QFont("Arial", 13))
        self.barcode_input.setPlaceholderText("Enter or Scan Barcode Here")
        self.barcode_input.returnPressed.connect(self.process_barcode)
        scanning_layout.addWidget(self.barcode_input, 2)

        # Process Button
        self.process_button = QPushButton("Process Check-In")
        self.process_button.setFont(QFont("Arial", 13))
        self.process_button.clicked.connect(self.process_barcode)
        scanning_layout.addWidget(self.process_button, 1)

        main_layout.addWidget(scanning_frame)

        # -- STATUS MESSAGE BELOW ENTRY FIELD --
        self.status_label = QLabel("")  # Initially empty
        self.status_label.setFont(QFont("Arial", 11))
        self.status_label.setStyleSheet("color: #007BFF;")  # Blue text
        main_layout.addWidget(self.status_label)

        # -- RESULTS TABLE --
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(
            ["Barcode", "Title", "Author", "Call Number", "Status", "Action Taken"]
        )

        # Bold the table header labels
        font_header = self.results_table.horizontalHeader().font()
        font_header.setBold(True)
        self.results_table.horizontalHeader().setFont(font_header)

        # Stretch columns to fill available space
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Optionally hide the vertical header if not needed
        # self.results_table.verticalHeader().setVisible(False)

        # Use alternating row colors
        self.results_table.setAlternatingRowColors(True)
        # Remove grid lines for a cleaner look
        self.results_table.setShowGrid(False)

        # Custom styling for the table
        self.results_table.setStyleSheet("""
            QTableView {
                selection-background-color: #D0F0FF; /* Light highlight */
                background-color: #ffffff;          /* Table background color */
            }
        """)

        main_layout.addWidget(self.results_table)

        # -- ROW COUNT LABEL --
        self.row_count_label = QLabel("Total Books Scanned: 0")
        self.row_count_label.setFont(QFont("Arial", 11))
        main_layout.addWidget(self.row_count_label, alignment=Qt.AlignRight)

        # -- FINISH UP --
        self.setCentralWidget(container)
        self.setMinimumSize(900, 600)  # Comfortable window size

    def get_access_token(self):
        """
        Fetch OAuth token required for API requests.
        """
        if self.token_info and "access_token" in self.token_info and self.token_info.get(
                "expires_at", 0
                ) > time.time():
            return self.token_info["access_token"]

        auth = HTTPBasicAuth(config["wskey"], config["secret"])
        data = {"grant_type": "client_credentials", "scope": config["scope"]}
        try:
            logging.debug(f"Requesting access token: {config['oauth_server_token']}")
            logging.debug(f"Request payload: {data}")
            response = requests.post(
                config["oauth_server_token"], auth=auth, data=data, timeout=10
                )  # Set timeout to 10 seconds
            logging.debug(f"Response status code: {response.status_code}")
            logging.debug(f"Response headers: {response.headers}")
            logging.debug(f"Response content: {response.text}")
            response.raise_for_status()

            token_data = response.json()
            logging.debug(f"Fetched access token: {token_data}")

            # Store token and expiry time
            self.token_info = {
                "access_token": token_data["access_token"],
                "expires_at": time.time() + token_data.get("expires_in", 3600) - 60,
                }
            return self.token_info["access_token"]
        except requests.Timeout:
            logging.error("Timeout occurred while fetching OAuth token.")
            raise
        except requests.RequestException as e:
            logging.error(f"Error during OAuth token request: {e}")
            raise

    def process_barcode(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            QMessageBox.warning(self, "Error", "Please enter a barcode.")
            logging.warning("No barcode entered.")
            self.barcode_input.setFocus()
            return

        # Show processing message and clear input field
        self.status_label.setText(f"Processing barcode {barcode}...")
        self.barcode_input.clear()
        self.barcode_input.setFocus()  # Keep the input field active

        self.set_loading_state(True)
        try:
            logging.info(f"Processing barcode: {barcode}")

            # Retry logic for OCLC lookup
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    # 1. Lookup OCLC number
                    oclc_data = self.lookup_oclc_number(barcode)
                    if 'error' in oclc_data:
                        raise Exception(oclc_data['error'])

                    oclc_number = oclc_data.get('oclcNumber')
                    if not oclc_number:
                        QMessageBox.warning(self, "Error", "No OCLC number found for this barcode.")
                        return

                    # 2. Check availability
                    response_xml = self.check_availability(oclc_number)
                    status = self.parse_availability(response_xml, barcode)
                    if 'error' in status:
                        raise Exception(status['error'])

                    # 3. Handle special cases like TRANSIT
                    if status.get('reasonUnavailable') == "TRANSIT":
                        self.add_result_to_table(barcode, status, "None", is_error=True)
                        return

                    # 4. Take action
                    if status.get('checkedOut'):
                        action_response = self.check_in_item(barcode)
                        status["status"] = action_response["status"]
                        action_taken = action_response["action"]
                    elif status.get('status') == "Available":
                        self.non_loan_return(barcode)
                        status["status"] = "In-Library Use"
                        action_taken = "In-Library Use"
                    else:
                        QMessageBox.warning(
                            self, "Warning",
                            f"Item status: {status['status']}. {status.get('reasonUnavailable', '')}"
                            )
                        return

                    # 5. Update table
                    self.add_result_to_table(barcode, status, action_taken)
                    break  # Break the retry loop on success

                except Exception as e:
                    logging.error(
                        f"Error processing barcode {barcode} (attempt {attempt + 1}): {str(e)}"
                        )
                    if attempt < max_retries:
                        logging.info("Retrying after failure...")
                        self.token_info = None  # Invalidate the token to force a refresh
                    else:
                        QMessageBox.critical(
                            self, "Error",
                            f"An error occurred while processing {barcode}.\n\nDetails:\n{str(e)}"
                            )
                        self.add_result_to_table(
                            barcode, {
                                "status": "Error", "title": "Unknown", "author": "Unknown",
                                "callNumber": "Unknown"
                                }, "None", is_error=True
                            )
        finally:
            self.status_label.clear()  # Clear the status message
            self.set_loading_state(False)
            self.barcode_input.setFocus()

    def set_loading_state(self, is_loading):
        self.barcode_input.setEnabled(not is_loading)
        self.process_button.setEnabled(not is_loading)
        self.process_button.setText("Processing..." if is_loading else "Process Check-In")

    def lookup_oclc_number(self, barcode):
        """
        Lookup OCLC number using the barcode via the Discovery API.
        """
        try:
            url = f"{config['discovery_api_url']}/search/my-holdings"
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}", "Accept": "application/json",
                }
            logging.debug(f"Requesting OCLC lookup: {url}")
            logging.debug(f"Request headers: {headers}")
            response = requests.get(f"{url}?barcode={barcode}", headers=headers, timeout=10)
            logging.debug(f"Response status code: {response.status_code}")
            logging.debug(f"Response headers: {response.headers}")
            logging.debug(f"Response content: {response.text}")
            response.raise_for_status()

            data = response.json()
            if data.get("numberOfHoldings", 0) == 0:
                return {"error": "No holdings found for this barcode."}

            holding = data["detailedHoldings"][0]
            return {
                "barcode": barcode, "oclcNumber": holding.get("oclcNumber", "Unknown OCLC Number"),
                }
        except requests.Timeout:
            logging.error("Timeout occurred during OCLC lookup.")
            raise Exception("The request to OCLC timed out. Please try again.")
        except requests.RequestException as e:
            logging.error(f"Error during OCLC lookup: {e}")
            return {"error": str(e)}

    def check_availability(self, oclc_number):
        """
        Check availability for an item using OCLC's Availability API.
        """
        host = "worldcat.org"
        path = (f"/circ/availability/sru/service?x-registryId="
                f"{config['institution_id']}&query=no:{urllib.parse.quote(oclc_number)}")
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}", "Accept": "*/*"
            }

        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        conn = None
        try:
            logging.debug(f"Connecting to host: {host}")
            logging.debug(f"Request path: {path}")
            logging.debug(f"Request headers: {headers}")
            conn = http.client.HTTPSConnection(host, context=context, timeout=10)
            conn.request("GET", path, headers=headers)
            response = conn.getresponse()
            response_data = response.read().decode("utf-8")

            logging.debug(f"Response status: {response.status}")
            logging.debug(f"Response headers: {response.getheaders()}")
            logging.debug(f"Response body: {response_data}")

            if response.status == 200:
                return response_data
            else:
                raise Exception(f"HTTP {response.status}: {response_data}")

        except http.client.HTTPException as e:
            logging.error(f"HTTP error during availability check: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during availability check: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    def parse_availability(xml_response, item_barcode):
        try:
            root = ET.fromstring(xml_response)
            namespaces = {"srw": "http://www.loc.gov/zing/srw/"}

            holdings = root.findall(".//srw:recordData/opacRecord/holdings/holding", namespaces)
            if not holdings:
                return {"error": "No holdings found in XML response."}

            for holding in holdings:
                circulations = holding.findall(".//circulations/circulation")
                for circulation in circulations:
                    item_id = circulation.find(".//itemId")
                    if item_id is not None and item_id.text == item_barcode:
                        available_now = circulation.find(".//availableNow[@value='1']")
                        availability_date = circulation.find(".//availabilityDate")
                        reason_unavailable = circulation.find(".//reasonUnavailable")

                        if available_now is not None:
                            status = "Available"
                            reason = None
                            availability_date_text = None
                        else:
                            status = "Unavailable"
                            reason = reason_unavailable.text if reason_unavailable is not None else "No reason"
                            availability_date_text = availability_date.text if availability_date is not None else "N/A"

                        # Check if the item is currently checked out or overdue
                        is_checked_out = (reason in ["ON_LOAN", "OVERDUE",
                                                     "LONG_OVERDUE"]) if status == "Unavailable" else False

                        # Extract bibliographic info
                        title_field = root.find(".//bibliographicRecord/record/datafield[@tag='245']/subfield[@code='a']")
                        title = title_field.text if title_field is not None else "Unknown Title"

                        author_field = root.find(".//bibliographicRecord/record/datafield[@tag='100']/subfield[@code='a']")
                        if author_field is None:
                            author_field = root.find(".//bibliographicRecord/record/datafield[@tag='700']/subfield[@code='a']")
                        author = author_field.text if author_field is not None else "Unknown Author"

                        call_number_field = holding.find(".//callNumber")
                        call_number = call_number_field.text if call_number_field is not None else "N/A"

                        return {
                            "barcode": item_id.text,
                            "title": title,
                            "author": author,
                            "callNumber": call_number,
                            "status": status,
                            "availabilityDate": availability_date_text if status == "Unavailable" else None,
                            "reasonUnavailable": reason if status == "Unavailable" else None,
                            "checkedOut": is_checked_out,
                        }

            return {"error": "Item barcode not found in holdings"}

        except ET.ParseError as e:
            return {"error": f"Failed to parse XML: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @staticmethod
    def fetch_ncip_access_token():
        try:
            auth = HTTPBasicAuth(config["wskey"], config["secret"])
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {"grant_type": "client_credentials", "scope": config["scope"]}

            response = requests.post(config["oauth_server_token"], headers=headers, auth=auth, data=data, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            logging.debug(f"NCIP Access Token Response: {token_data}")
            return token_data.get("access_token")

        except requests.RequestException as e:
            logging.error(f"Error fetching NCIP access token: {e}")
            raise

    def check_in_item(self, barcode):
        """
        Attempt to check in the item via the NCIP API.
        """
        ncip_request = f"""<?xml version="1.0" encoding="UTF-8"?>
        <NCIPMessage xmlns="http://www.niso.org/2008/ncip" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:ncip="http://www.niso.org/2008/ncip"
            xsi:schemaLocation="http://www.niso.org/2008/ncip http://www.niso.org/schemas/ncip/v2_01/ncip_v2_01.xsd"
            ncip:version="http://www.niso.org/schemas/ncip/v2_01/ncip_v2_01.xsd">
            <CheckInItem>
                <InitiationHeader>
                    <FromAgencyId>
                        <AgencyId ncip:Scheme="http://oclc.org/ncip/schemes/agencyid.scm">{config['registry_id']}</AgencyId>
                    </FromAgencyId>
                    <ToAgencyId>
                        <AgencyId>{config['registry_id']}</AgencyId>
                    </ToAgencyId>
                    <ApplicationProfileType ncip:Scheme="http://oclc.org/ncip/schemes/application-profile/platform.scm">Version 2011</ApplicationProfileType>
                </InitiationHeader>
                <ItemId>
                    <AgencyId>{config['institution_id']}</AgencyId>
                    <ItemIdentifierValue>{barcode}</ItemIdentifierValue>
                </ItemId>
            </CheckInItem>
        </NCIPMessage>"""

        token = self.fetch_ncip_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/xml"
        }

        logging.debug(f"NCIP Check-In Request: {ncip_request}")
        logging.debug(f"Request headers: {headers}")
        response = requests.post(config["ncip_api_url"], headers=headers, data=ncip_request)
        logging.debug(f"Response status code: {response.status_code}")
        logging.debug(f"Response headers: {response.headers}")
        logging.debug(f"Response content: {response.text}")
        response.raise_for_status()

        root = ET.fromstring(response.text)
        namespaces = {"ns1": "http://www.niso.org/2008/ncip"}

        problem = root.find(".//ns1:Problem", namespaces)
        if problem is not None:
            problem_type = problem.find(".//ns1:ProblemType", namespaces)
            problem_detail = problem.find(".//ns1:ProblemDetail", namespaces)
            problem_message = (
                f"Problem Type: {problem_type.text if problem_type is not None else 'Unknown'}, "
                f"Detail: {problem_detail.text if problem_detail is not None else 'No detail'}"
            )
            raise Exception(f"Check-in failed with problem: {problem_message}")

        routing_instructions = root.find(".//ns1:RoutingInstructions", namespaces)
        routing_status = routing_instructions.text if routing_instructions is not None else "Unknown"

        return {"status": routing_status, "action": "Checked In"}

    def non_loan_return(self, barcode):
        """
        Mark item as non-loan return.
        """
        try:
            url = f"https://{config['institution_id']}.share.worldcat.org/circ/items/{barcode}/routings/usages"
            payload = {
                "location": f"https://{config['institution_id']}.share.worldcat.org/circ/branches/{config['registry_id']}"
                }
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
                }

            logging.debug(f"Non-loan return request URL: {url}")
            logging.debug(f"Request payload: {json.dumps(payload, indent=2)}")
            logging.debug(f"Request headers: {headers}")

            response = requests.post(url, headers=headers, json=payload)

            logging.debug(f"Response status code: {response.status_code}")
            logging.debug(f"Response headers: {response.headers}")
            logging.debug(f"Response content: {response.text}")

            response.raise_for_status()

            response_data = response.json()
            logging.info(
                f"Non-loan return completed successfully for barcode {barcode}. Response: {response_data}"
                )

            return {"success": True, "data": response_data}
        except requests.Timeout:
            logging.error(f"Timeout occurred while marking non-loan return for barcode {barcode}.")
            raise
        except requests.RequestException as e:
            logging.error(f"Error during non-loan return for barcode {barcode}: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in non-loan return for barcode {barcode}: {e}")
            raise

    def add_result_to_table(self, barcode, status, action_taken, is_error=False, extra_details=None):
        """
        Adds a new row to the results table with the processed data.
        Also updates the 'Total Books Scanned' label and optionally highlights errors.
        """
        row_position = self.results_table.rowCount()
        self.results_table.insertRow(row_position)

        # Determine the displayable status
        status_text = status.get("reasonUnavailable", status.get("status", "Unknown"))

        self.results_table.setItem(row_position, 0, QTableWidgetItem(barcode))
        self.results_table.setItem(row_position, 1, QTableWidgetItem(status.get("title", "Unknown")))
        self.results_table.setItem(row_position, 2, QTableWidgetItem(status.get("author", "Unknown")))
        self.results_table.setItem(row_position, 3, QTableWidgetItem(status.get("callNumber", "N/A")))
        self.results_table.setItem(row_position, 4, QTableWidgetItem(status_text))
        self.results_table.setItem(row_position, 5, QTableWidgetItem(action_taken))

        if extra_details:
            # If you ever add a 7th column for details, you could set it here
            pass

        # Highlight error rows in red
        if is_error:
            for col in range(self.results_table.columnCount()):
                item = self.results_table.item(row_position, col)
                if item:
                    item.setForeground(QColor(255, 0, 0))

        # Update the "Total Books Scanned" label
        total_count = self.results_table.rowCount()
        self.row_count_label.setText(f"Total Books Scanned: {total_count}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("app_icon.ico")))
    window = BookCheckInApp()
    window.show()
    sys.exit(app.exec_())
