# inoculator-test
This repository contains automated test scripts built using **Playwright**. These scripts aim to provide reliable, fast, and end-to-end testing for web applications.

---

## Features

* Cross-browser testing (Chromium, Firefox, WebKit)
* Headed and headless modes
* Automatic waiting for elements
* Parallel execution support
* Easy test configuration using Playwright Test Runner
* Screenshot and trace generation for debugging

---

##  Project Structure

```
project-root/
│
├── tests/               # Contains all test scripts
├── fixtures/            # Shared test data or reusable components
├── pages/               # Page Object Model (POM) files
├── playwright.config.js # Main configuration file
└── package.json         # Dependencies and npm scripts
```

---

##  Installation

1. Install Node.js (LTS version recommended)
2. Clone the repository
3. Install dependencies:

```
npm install
```

4. Install Playwright browsers:

```
npx playwright install
```

---

##  Running Tests

### Run all tests

```
npx playwright test
```

### Run tests in headed mode

```
npx playwright test --headed
```

### Run a specific test file

```
npx playwright test tests/example.spec.js
```

### Run with UI Test Explorer

```
npx playwright test --ui
```

---

##  Test Reports

Playwright automatically generates reports.

### View HTML report

```
npx playwright show-report
```

Reports include:

* Test status
* Screenshots
* Videos
* Trace viewer

---

##  Writing Tests (Basic Example)

```javascript
import { test, expect } from '@playwright/test';

test('example test', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example/);
});
```

---

##  Using Page Object Model (POM)

Example structure:

```javascript
// pages/LoginPage.js
class LoginPage {
  constructor(page) {
    this.page = page;
    this.username = page.locator('#username');
    this.password = page.locator('#password');
    this.loginBtn = page.locator('#login');
  }

  async login(user, pass) {
    await this.username.fill(user);
    await this.password.fill(pass);
    await this.loginBtn.click();
  }
}
export default LoginPage;
```

---

## Configuration (playwright.config.js)

Common settings include:

* Default timeout
* Retries
* Reporter type
* Screenshot & video settings
* Browser settings

---

##  Contribution Guidelines

* Follow consistent code formatting
* Use meaningful test descriptions
* Store reusable selectors in POM files
* Add comments where necessary

---

##  License

This project is licensed under your preferred license (MIT, Apache, etc.).
