\# WebSentinel-AI



\### AI-Assisted Automated Web Testing Platform with Self-Healing Locators



\*\*WebSentinel-AI\*\* is an automated web testing platform designed to simplify end-to-end testing through intelligent website crawling, automated test generation, real-browser execution, self-healing locators, and evidence-based reporting.



Simply provide a website URL. WebSentinel-AI explores the website using a real browser, generates test cases, executes them automatically, attempts to recover broken selectors when the interface changes, and produces detailed bug reports through its dashboard and PDF reporting system.



The platform aims to reduce repetitive manual testing and make automated UI testing more resilient without requiring users to write test code manually.



\---



\## ✨ Key Features



| #  | Feature                   | Description                                                                                                                                                                            |

| -- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

| 01 | Smart Website Crawler     | Uses Playwright and headless Chromium to explore in-scope pages, extract links, buttons, and forms, classify common form types, and detect HTTP 4xx/5xx responses.                     |

| 02 | Automatic Test Generation | Generates smoke, navigation, functional, validation, negative, and security-oriented test cases using a rule-based engine. Optional LLM integration can suggest additional edge cases. |

| 03 | Live Test Execution       | Executes generated tests in a real browser and streams execution progress, logs, and events to the dashboard using Server-Sent Events (SSE).                                           |

| 04 | Self-Healing Locators     | Uses element fingerprints and weighted similarity scoring to identify replacement elements when original selectors become invalid.                                                     |

| 05 | Comprehensive Reporting   | Displays execution summaries, pass rates, failures, healed selectors, bug severity information, screenshots, and PDF reports.                                                          |

| 06 | Test Export               | Exports generated test cases as standalone `pytest-playwright` scripts for potential integration into external testing workflows.                                                      |

| 07 | Root Cause Analysis       | Groups related failures and provides observed evidence, affected tests, likely causes, confidence estimates, and suggested fixes using transparent offline rules.                      |

| 08 | Built-in Demo Website     | Includes an offline ShopLite demo with three intentional bugs and a v2 redesign mode for demonstrating locator recovery.                                                               |

| 09 | Bug Replay Capsule        | Packages failure details, available screenshots, console errors, root-cause hints, and replay instructions into a downloadable ZIP file.                                               |



\---



\## 🏗️ System Architecture



WebSentinel-AI follows a modular architecture with a React-based frontend, FastAPI backend, browser automation layer, and SQLite database.



```text

&#x20;                React + Tailwind Dashboard

&#x20;                          |

&#x20;                    REST + SSE

&#x20;                          |

&#x20;                   FastAPI Backend

&#x20;                          |

&#x20;      ┌───────────────────┼───────────────────┐

&#x20;      |                   |                   |

&#x20;  crawler.py          generator.py         runner.py

&#x20;  Website crawling    Rule-based tests     Test execution

&#x20;  DOM extraction      Optional LLM         Live events

&#x20;      |                   |                   |

&#x20;      └───────────────────┼───────────────────┘

&#x20;                          |

&#x20;                   healer.py

&#x20;                 Locator recovery

&#x20;                          |

&#x20;                  root\_cause.py

&#x20;               Failure analysis

&#x20;                          |

&#x20;                    report.py

&#x20;                  PDF reporting

&#x20;                          |

&#x20;      ┌───────────────────┼───────────────────┐

&#x20;      |                   |                   |

&#x20;  exporter.py           db.py             demo\_site.py

&#x20;  Test export          SQLite DB          ShopLite demo

```



\### Technology Stack



| Layer              | Technologies                             |

| ------------------ | ---------------------------------------- |

| Frontend           | React 19, TypeScript, Vite, Tailwind CSS |

| Backend            | Python, FastAPI, Uvicorn, Pydantic       |

| Browser Automation | Playwright, Chromium                     |

| Database           | SQLite                                   |

| HTTP Client        | httpx                                    |

| PDF Generation     | ReportLab                                |

| Data Visualization | Recharts                                 |

| Icons              | lucide-react                             |

| Testing            | pytest, pytest-asyncio, pytest-cov       |

| Code Quality       | Ruff, ESLint, TypeScript Strict Mode     |

| Optional AI        | Ollama or OpenAI API                     |

| CI/CD              | GitHub Actions                           |



\---



\## ⚙️ How It Works



The platform follows an automated testing workflow:



1\. \*\*Website Input:\*\* The user provides a target website URL.

2\. \*\*Website Crawling:\*\* The crawler explores pages within the configured website scope.

3\. \*\*DOM Extraction:\*\* Links, buttons, forms, and interactive elements are identified.

4\. \*\*Test Generation:\*\* The rule engine generates relevant test scenarios from discovered elements.

5\. \*\*Browser Execution:\*\* Playwright executes the generated tests in Chromium.

6\. \*\*Self-Healing:\*\* When an original locator fails, the system attempts to identify a matching element using its stored fingerprint.

7\. \*\*Failure Analysis:\*\* Related failures are grouped and analyzed using deterministic rules.

8\. \*\*Reporting:\*\* Results, evidence, screenshots, and suggested fixes are presented through the dashboard and PDF reports.



\---



\## 🔍 Core Functional Modules



\### 1. Smart Website Crawler



The crawler uses Playwright with Chromium to explore the target website.



It can:



\- Discover pages within the configured website scope.

\- Extract links, buttons, forms, and interactive elements.

\- Collect DOM information and element attributes.

\- Classify common forms, including login, search, and contact forms.

\- Identify HTTP 4xx and 5xx responses.

\- Maintain a configurable page limit to control crawling.



\### 2. Automatic Test Generation



A rule-based engine generates test cases based on the discovered website structure.



Supported test categories include:



\- Smoke Testing

\- Navigation Testing

\- Functional Testing

\- Form Validation Testing

\- Negative Testing

\- Security-Oriented Input Testing



Example test scenarios:



\- Empty required-field submission.

\- Invalid email input.

\- Invalid login attempts.

\- Special-character input.

\- XSS/SQL-related input patterns.



\*\*Optional LLM Integration\*\*



The platform can optionally use a local Ollama model or OpenAI to suggest additional edge-case scenarios.



LLM-generated suggestions are validated against discovered website elements before being used.



The default rule-based workflow operates without an LLM.



\### 3. Live Browser Test Execution



Generated test cases are executed using Playwright in a real Chromium browser.



The dashboard provides:



\- Live execution progress.

\- Browser execution view.

\- Test status updates.

\- Execution logs.

\- Failure information.

\- Available screenshots and evidence.



The platform can optionally open a visible browser window with slow-motion execution for demonstration purposes.



Live updates are streamed using Server-Sent Events (SSE).



\### 4. Self-Healing Locator Engine



One of the central features of WebSentinel-AI is its fingerprint-based locator recovery mechanism.



Traditional automated tests often depend on fixed CSS selectors, IDs, or XPath expressions. When a website's interface changes, these selectors may become invalid.



WebSentinel-AI attempts to recover from certain selector changes by comparing stored element fingerprints with the current page elements.



\*\*Element fingerprint information includes:\*\*



\- HTML tag

\- ID

\- Name

\- Input type

\- Visible text

\- Label

\- Placeholder

\- CSS classes

\- Form context

\- DOM path



\*\*Matching Process:\*\*



1\. The original locator is used to locate the target element.

2\. If the locator fails, the system examines current page elements.

3\. Stored fingerprints are compared with candidate elements.

4\. A weighted similarity score is calculated.

5\. The best candidate is evaluated against the matching threshold.

6\. Ambiguous or low-confidence matches are rejected.

7\. If a sufficiently reliable match is found, the locator is recovered and the test can continue.



\*\*Current matching threshold: 65% (0.65).\*\*



The system also checks for near-tied candidates to reduce the risk of selecting the wrong element.



\*\*Important limitation:\*\* Self-healing repairs a test locator, not the website's underlying functionality. It does not automatically fix broken application logic, missing features, server errors, or incorrect business rules.



\### 5. Root Cause Analysis



WebSentinel-AI includes a deterministic, rule-based failure analysis module.



It groups related failures and presents:



\- Failure category.

\- Observed evidence.

\- Affected test cases.

\- Likely cause.

\- Confidence estimate.

\- Suggested fixes.



The analysis uses transparent offline rules rather than requiring an external AI service.



\*\*Important:\*\* Root-cause findings are hypotheses based on available evidence. They are not guaranteed diagnoses and should be reviewed by a developer.



\### 6. Reporting and Test Export



The reporting module provides:



\- Total test count.

\- Passed and failed tests.

\- Pass rate.

\- Failure information.

\- Healed locator count.

\- Bug severity information.

\- Available failure screenshots.

\- Quality trends across runs.

\- One-click PDF report generation.



Generated test cases can also be exported as standalone `pytest-playwright` scripts.



\### 7. Bug Replay Capsule



WebSentinel-AI includes a Bug Replay Capsule mechanism for failed or errored test results.



Each available capsule is packaged as a downloadable ZIP file containing:



```text

Bug-Replay-Capsule/

│

├── capsule.json

│

├── README.txt

│

└── evidence/

&#x20;   ├── failure-evidence.txt

&#x20;   └── screenshot.png

```



The contents may include:



\- Project and run metadata.

\- Failing test case and execution steps.

\- Failed step information.

\- Error details.

\- Browser console errors.

\- Related root-cause hints.

\- Replay instructions.

\- Failure screenshot, when available.



The capsule makes failure evidence easier to share between developers, testers, and reviewers.



Common password, token, and secret step values are redacted. However, other test inputs or error messages may still contain personal information, so capsules should be reviewed before sharing.



\*\*API Endpoint:\*\*



```http

GET /api/runs/{run\_id}/capsules/{result\_index}

```



`result\_index` is zero-based.



\---



\## 🧪 Built-in ShopLite Demo



WebSentinel-AI includes an offline demonstration website called \*\*ShopLite\*\*.



It contains three intentional bugs:



| Demo Bug              | Expected Behavior                                                    |

| --------------------- | -------------------------------------------------------------------- |

| Broken Careers Link   | Navigation leads to a missing-page response.                         |

| Weak Email Validation | The form accepts an invalid email value.                             |

| Search Server Error   | Special-character search input triggers an intentional server error. |



The demo also includes a v2 redesign switch that changes element identifiers, classes, and text while keeping the underlying interactions available.



This allows users to demonstrate the self-healing locator mechanism without depending on an external website.



\### Demonstrating Self-Healing Locators



Follow these steps:



1\. Start WebSentinel-AI.

2\. Open the built-in demo at `http://localhost:8000/demo/`.

3\. Keep the demo website on v1.

4\. Click \*\*Crawl Site\*\*.

5\. Click \*\*Generate Tests\*\* to record the original element locators.

6\. Click \*\*Deploy v2 Redesign\*\* to change the UI selectors.

7\. Open \*\*Live Run\*\*.

8\. Keep \*\*Self-Healing Locators\*\* enabled.

9\. Execute the generated tests.



When a matching element is found, the execution log should show a self-healing event similar to:



```text

Self-healed: old selector → new selector

```



The affected test may then be marked as:



```text

passed (healed)

```



The actual result depends on whether the system finds a sufficiently similar and unambiguous element.



\---



\## 🚀 Installation and Quick Start



\### Requirements



\- Python 3.10+

\- Node.js 18+

\- npm

\- Chromium browser support through Playwright



\### Start the Application



\*\*Linux / macOS\*\*



```bash

./start.sh

```



\*\*Windows\*\*



```bat

start.bat

```



After starting the application, open:



```text

http://localhost:8000

```



Then select:



\*\*Try the built-in demo store\*\*



\---



\## 🛠️ Development Mode



\### 1. Create a Python Virtual Environment



```bash

python3 -m venv .venv

```



\### 2. Install Backend Development Dependencies



```bash

.venv/bin/pip install -r backend/requirements-dev.txt

```



\### 3. Install Playwright Chromium



```bash

.venv/bin/python -m playwright install chromium

```



\### 4. Start the Backend



```bash

cd backend

../.venv/bin/uvicorn app.main:app --reload --port 8000

```



\### 5. Start the Frontend



Open another terminal:



```bash

cd frontend

npm install

npm run dev

```



The frontend development server runs on:



```text

http://localhost:5173

```



\---



\## 🤖 Optional LLM Integration



WebSentinel-AI works offline using its default rule-based test generation engine.



An optional LLM can be enabled to suggest additional test scenarios.



\### Option 1: Local Ollama



Install Ollama and download a model:



```bash

ollama pull qwen2.5:1.5b

```



Run the application with:



```bash

TESTPILOT\_LLM=ollama OLLAMA\_MODEL=qwen2.5:1.5b ./start.sh

```



\### Option 2: OpenAI



Configure the OpenAI API key:



```bash

TESTPILOT\_LLM=openai OPENAI\_API\_KEY=your-api-key ./start.sh

```



Never commit real API keys or secrets to GitHub.



\### Environment Variables



| Variable             | Default                  | Description                                    |

| -------------------- | ------------------------ | ---------------------------------------------- |

| `TESTPILOT\_LLM`      | `none`                   | Selects `none`, `ollama`, `openai`, or `auto`. |

| `OLLAMA\_URL`         | `http://localhost:11434` | Local Ollama server URL.                       |

| `OLLAMA\_MODEL`       | `qwen2.5:1.5b`           | Local LLM model name.                          |

| `OPENAI\_API\_KEY`     | Not configured           | OpenAI API authentication key.                 |

| `OPENAI\_MODEL`       | `gpt-4o-mini`            | OpenAI model name.                             |

| `TESTPILOT\_DATA\_DIR` | `./data`                 | Directory for SQLite database and screenshots. |

| `TESTPILOT\_HEADLESS` | `1`                      | Set to `0` to display the browser by default.  |



\---



\## ✅ Quality Assurance and Testing



WebSentinel-AI includes automated testing and code-quality checks for the platform itself.



\### Testing and Quality Tools



\- pytest

\- pytest-asyncio

\- pytest-cov

\- Ruff

\- ESLint

\- TypeScript Strict Mode

\- GitHub Actions



\### Test Coverage and CI



The project documentation describes an automated QA suite with:



\- Unit testing.

\- API testing.

\- End-to-end testing.

\- Code coverage measurement.

\- Python linting.

\- Frontend linting and build checks.



The documented CI configuration uses GitHub Actions to run linting, tests, coverage checks, and frontend builds on pushes.



\*\*Documented QA target:\*\* At least 80% code coverage.



\### Run Backend Tests



```bash

cd backend

../.venv/bin/pytest --cov=app

```



\### Current Source Package Verification



The following verification status applies to the inspected source package:



| Verification              | Status                                                       |

| ------------------------- | ------------------------------------------------------------ |

| Backend non-browser tests | 34 passed                                                    |

| Browser end-to-end test   | Not successfully executed in the inspected build environment |

| Frontend production build | Not verified in the inspected build environment              |



The browser E2E test could not be successfully executed because the Playwright Chromium executable was not installed in that environment.



Install Chromium before running browser-based tests:



```bash

python -m playwright install chromium

```



The frontend production build was not verified because dependency installation did not complete in that environment.



These environment-specific verification limitations should be considered when interpreting the test results.



\---



\## 🔄 Reliability Improvements



The platform includes several improvements intended to make testing and failure reporting more reliable.



\### Duplicate Failure Grouping



Repeated failures with the same normalized test title and error are grouped as one unique bug in the run summary.



Individual test results remain available for traceability.



\### Duplicate Test Prevention



Equivalent invalid-field assertions are de-duplicated during test generation, including overlapping heuristic and LLM-generated cases targeting the same field.



\### Improved Search Form Recognition



Search forms are identified using multiple element attributes, including:



\- Input type.

\- Name.

\- ID.

\- Placeholder.

\- Accessible label.



The special-character search test checks the resulting main-document HTTP status. A 5xx response is reported as a failure.



\### Improved Bug Replay Evidence



Bug Replay Capsules can include:



\- `capsule.json`

\- Replay instructions.

\- `evidence/failure-evidence.txt`

\- Failure screenshots, when available.



\---



\## 📚 Project Documentation



The following documents provide detailed information about WebSentinel-AI, including its design, implementation, architecture, and testing.



| Document                                                                        | Description                                                |

| ------------------------------------------------------------------------------- | ---------------------------------------------------------- |

| \[Project Report](docs/WebSentinel\_AI\_Project\_Report.pdf)                        | Complete technical documentation of the project.           |

| \[Test Report 01](docs/WebSentinel\_AI\_Test\_Report\_01.pdf)                        | First testing report with test results and evidence.       |

| \[Test Report 02](docs/WebSentinel\_AI\_Test\_Report\_02.pdf)                        | Second testing report with test results and evidence.      |



\*Make sure the PDF files are uploaded to the exact paths shown above.\*



\---



\## 🔐 Security and Responsible Use



\- Use WebSentinel-AI only on websites you own or have permission to test.

\- Do not commit API keys, credentials, or private configuration files.

\- Review screenshots, test inputs, logs, and replay capsules before sharing.

\- Security-oriented input checks are basic automated tests, not a complete security audit.

\- Automated test results should be reviewed before making production decisions.



\---



\## ⚠️ Current Limitations



\- Locator recovery is heuristic and may not succeed after every interface redesign.

\- Ambiguous or low-confidence locator matches are rejected.

\- Root-cause analysis provides evidence-based hypotheses rather than guaranteed diagnoses.

\- Generated tests depend on the website elements and behavior discovered by the crawler.

\- Browser coverage and compatibility depend on the installed environment and target website.

\- Security-oriented tests do not replace professional penetration testing.

\- Optional LLM functionality depends on the selected provider and its availability.



\---



\## 🔮 Future Enhancements



Potential future development areas include:



\- Visual regression testing.

\- Advanced API testing.

\- Scheduled automated test execution.

\- Multi-browser testing support.

\- CI/CD integration improvements.

\- Issue-tracking platform integration.

\- More advanced failure analysis.

\- Enhanced test coverage and reporting.



\---



\## 💡 Project Innovation



WebSentinel-AI brings several automated testing capabilities together in one platform:



\*\*Discover → Generate → Execute → Heal → Analyze → Report\*\*



Its main contribution is the integration of website crawling, rule-based test generation, real-browser execution, fingerprint-based locator recovery, failure analysis, and portable bug evidence.



Rather than silently hiding failures, the platform attempts locator recovery only when a sufficiently reliable candidate is identified.



\---



\## 👨‍💻 Project Information



\*\*Project Name:\*\* WebSentinel-AI



\*\*Project Category:\*\* Automated Software Testing / Web Test Automation



\*\*Primary Technologies:\*\* Python, FastAPI, React, TypeScript, Playwright, Chromium, SQLite



\*\*Core Focus:\*\* Automated web testing, self-healing locators, failure analysis, and reporting.



\---





