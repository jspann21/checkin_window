# Library Book Check-In System

A desktop application built with PyQt5 that automatically determines whether a book should be processed as a check-in or a non-loan return in OCLC's WorldShare Management Services (WMS).

## Problem & Solution

**Problem:** When checking in books in OCLC WMS, staff must manually determine if a book is currently checked out (requiring check-in) or not checked out (requiring non-loan return). This manual verification is time-consuming and prone to errors. OCLC needs to fix this.

**Solution:** This application automatically:
1. Scans the book's barcode
2. Queries OCLC's APIs to determine the book's current status
3. Automatically processes it as either a check-in or non-loan return
4. Displays the results in a clear, easy-to-read table

![Book Check-In System](screenshots/app_preview.png) *(Add your own screenshot here)*

## Features

- **Automatic Status Detection**: Intelligently determines whether a book needs check-in or non-loan return
- **Barcode Scanning**: Quick check-in process using barcode scanning or manual entry
- **Real-time Status Updates**: Instantly view the status of each scanned book
- **Detailed Information Display**: Shows title, author, call number, and current status
- **Error Handling**: Clear visual indicators for any issues during the check-in process
- **Activity Logging**: Comprehensive logging system for troubleshooting
- **Modern UI**: Clean, intuitive interface with responsive design

## Prerequisites

- Windows 10 or later
- OCLC WorldShare API credentials (WSKey)
- Internet connection

## API Key Setup

Before using this application, you'll need to request an API key from OCLC:

1. Visit [OCLC Developer Network](https://platform.worldcat.org/wskey/)
2. Click "Request A WSKey"
3. Select "Request a Custom Key"
4. Fill in the following details:
   - Type of Request: Production
   - Application Type: Machine-to-Machine (M2M) App
   - Required Services:
     - WMS Circulation API
     - WMS Availability
     - WorldCat Discovery API
     - WMS NCIP Service
   - WSKey Name: Self-Checkin
   - Reason for Request: "Automatically determine if a book is a non-loan return or a currently checked-out book and properly route it."
5. Complete the request and wait for OCLC's approval

## Installation

1. Download the latest release from the [Releases](../../releases) page
2. Extract the ZIP file to your desired location
3. Create a `config.json` file in the same directory as the executable (next to `Book Check-In Service.exe`) with your OCLC credentials:

```json
{
    "wskey": "your_wskey",
    "secret": "your_secret",
    "scope": "WMS_CIRCULATION WMS_Availability WorldCatDiscoveryAPI WMS_NCIP",
    "institution_id": "your_institution_id",
    "registry_id": "your_registry_id",
    "discovery_api_url": "https://discovery.api.oclc.org/worldcat-org-ci",
    "ncip_api_url": "https://circ.sd00.worldcat.org/ncip",
    "oauth_server_token": "https://oauth.oclc.org/token"
}
```

Configuration Notes:
- The `config.json` file must be placed in the same directory as the executable
- You can modify this file without rebuilding the application
- If no external config file is found, the application will not work
- `wskey`: Your Client ID from WSKey Management https://platform.worldcat.org/wskey/
- `secret`: Your Secret from WSKey Management https://platform.worldcat.org/wskey/
- `scope`: Leave as is - these are the required API scopes
- `institution_id`: The number beside your institution name on the main page at https://worldcat.org/config/
- `registry_id`: Your Branch Registry ID. Found at https://worldcat.org/config/ under:
  WorldCat Discovery and WorldCat Local > Holding Codes & Shelving Location Messages > 
  Holding Codes Translation Table
- `discovery_api_url`: Leave as is - this is the standard discovery API endpoint
- `ncip_api_url`: This varies depending on where your info is hosted. Options:
  - Try the default value shown above
  - Contact OCLC Help for your specific endpoint
  - See https://developer.api.oclc.org/wms-ncip-staff for more information
- `oauth_server_token`: Leave as is - this is the standard OAuth endpoint

4. Run `Book Check-In Service.exe`

## Building from Source

If you want to build the application from source:
```bash
git clone https://github.com/yourusername/library-checkin.git
cd library-checkin
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Build with PyInstaller:
```bash
pyinstaller --onefile --noconsole --add-data "config.json;." --add-data "app_icon.ico;." --add-data "barcode_icon.png;." --icon="app_icon.ico" --name "Book Check-In Service" checkin.py
```

The executable will be created in the `dist` directory.

## Usage

1. Launch the application
2. Scan book barcodes or enter them manually
3. The system will automatically:
   - Look up the OCLC number
   - Check item availability
   - Process the check-in
   - Display results in the table
4. Review the results table for any errors or special handling requirements

## Logging

The application maintains logs at:
- Windows: `C:\Users\<username>\.library_checkin\library_checkin.log`

Logs are rotated daily and kept for 14 days.

## Troubleshooting

Common issues and solutions:

1. **Configuration Error**: Ensure `config.json` is in the same directory as the executable
2. **API Connection Failed**: Verify internet connection and API credentials
3. **Barcode Not Found**: Confirm the barcode is registered in your OCLC system

## Development

The application is built using:
- Python 3.x
- PyQt5 for the GUI
- OCLC WorldShare APIs for library operations
- Requests library for API communication

## License

MIT License

Copyright (c) 2025 Library Book Check-In System

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Support

For support, please [create an issue](../../issues) or contact your system administrator.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request 