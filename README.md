<a id="readme-top"></a>

<!--
*** Thanks for checking out Q-pot! If you have improvements, please open an issue or PR.
*** Don't forget to give the project a ⭐ if you like it!
-->

<!-- PROJECT SHIELDS -->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]

<br />
<div align="center">
  <a href="https://github.com/your-org/q-pot">
    <img src="images/logo.png" alt="Q-pot Logo" width="80" height="80">
  </a>

  <h3 align="center">Q-pot (FinCoach)</h3>

  <p align="center">
    AI-powered financial coach for Bunq users
    <br />
    <a href="#quick-start"><strong>Get Started »</strong></a>
    <br /><br />
    <a href="https://github.com/your-org/q-pot">View Demo</a>
    &middot;
    <a href="https://github.com/your-org/q-pot/issues/new">Report Bug</a>
    &middot;
    <a href="https://github.com/your-org/q-pot/issues/new">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#built-with">Built With</a></li>
    <li><a href="#quick-start">Quick Start</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

---

## About The Project

Q-pot (FinCoach) is an AI-powered chat application that acts as your
personal financial advisor. It connects OpenAI’s GPT-4o with mock Bunq-style
tools (accounts, transactions, mortgage, investments, etc.) via an MCP
server—plus a DuckDuckGo search tool for external facts. The UI is a
simple scrollable chat (vanilla JS + FontAwesome), and everything ships
inside one Docker image you can deploy anywhere.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

- [FastAPI](https://fastapi.tiangolo.com/) – server & static hosting  
- [Uvicorn](https://www.uvicorn.org/) – ASGI server  
- [MCP](https://github.com/neuml/mcp) – multiplexed tool‐calling framework  
- [OpenAI Python](https://github.com/openai/openai-python) – LLM backend  
- [DuckDuckGo-Search](https://github.com/deedy5/duckduckgo-search) – web tool  
- Vanilla JavaScript + [Font Awesome](https://fontawesome.com/) – front-end  
- Docker – containerization

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Quick Start

### Prerequisites

- Python 3.11+  
- (Optional) Docker & Docker CLI  
- A valid OpenAI API key  

### Installation & Running Locally

1. **Clone the repo**

   ```sh
   git clone https://github.com/your-org/q-pot.git
   cd q-pot
   ```

2. **Create & populate your `.env`**

   ```sh
   cp .env.example .env
   # then open .env and set OPENAI_API_KEY, BUNQ_API_KEY, etc.
   ```

3. **Install dependencies**

   ```sh
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run the app**

   ```sh
   uvicorn chat_web.app:app --reload
   ```

5. **Open** [http://localhost:8000](http://localhost:8000)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Usage

- Type questions like “Help me budget for Japan” or
  “Show my investment portfolio performance.”  
- Use the Quick Actions or Conversation Starters to trigger common prompts.  
- The assistant will call the right tools (MCP endpoints) under the hood.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Roadmap

- [x] Mock tools: accounts, transactions, cards  
- [x] Web-search tool (DuckDuckGo) with TLS-tolerant fallback  
- [x] Mortgage & investment portfolio mock tools  
- [ ] Real Bunq API integration  
- [ ] Authentication & multi-user sessions  
- [ ] Persistent chat history  
- [ ] Deploy samples for Render / Fly.io

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contributing

1. Fork the Project  
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)  
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)  
4. Push to the Branch (`git push origin feature/AmazingFeature`)  
5. Open a Pull Request

Please read our [Contributing Guidelines](CONTRIBUTING.md) if available.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contact

Q-pot / FinCoach Team – [support@qpot.ai](mailto:support@qpot.ai)  
Project Link: [https://github.com/your-org/q-pot](https://github.com/your-org/q-pot)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Acknowledgments

- [Choose an Open Source License](https://choosealicense.com)  
- [Img Shields](https://shields.io)  
- [Font Awesome](https://fontawesome.com)  
- [Best README Template](https://github.com/othneildrew/Best-README-Template)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/your-org/q-pot.svg?style=for-the-badge
[contributors-url]: https://github.com/your-org/q-pot/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/your-org/q-pot.svg?style=for-the-badge
[forks-url]: https://github.com/your-org/q-pot/network/members
[stars-shield]: https://img.shields.io/github/stars/your-org/q-pot.svg?style=for-the-badge
[stars-url]: https://github.com/your-org/q-pot/stargazers
[issues-shield]: https://img.shields.io/github/issues/your-org/q-pot.svg?style=for-the-badge
[issues-url]: https://github.com/your-org/q-pot/issues
[license-shield]: https://img.shields.io/github/license/your-org/q-pot.svg?style=for-the-badge
[license-url]: https://github.com/your-org/q-pot/blob/main/LICENSE