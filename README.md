<!--
  Q-pot – README / landing page
  A polished, responsive HTML template that works both on GitHub (as
  inline HTML inside a .md file) and as a standalone page.
-->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Q-pot | AI-powered Financial Coach for Bunq</title>

  <!-- Bootstrap 5 – quick professional styling -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
        rel="stylesheet" integrity="sha384-IQsoLXl9+P+9Y+e5sGoRxFN2FAE1N/jd1GqZAq5AxZuUAvxQyiZAh+STThzJf6Ee"
        crossorigin="anonymous">

  <!-- Google Font -->
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap">

  <style>
    body   { font-family: "Inter", sans-serif; }
    h1,h2  { font-weight: 800; }
    code   { background:#f3f5f7;padding:.15rem .35rem;border-radius:.25rem }
    .hero  { background:linear-gradient(120deg,#ff3cac,#784ba0,#2b86c5);
             color:#fff; }
    .hero a{ color:#fff;text-decoration:underline }
    .feature-icon { font-size:1.75rem;color:#3b82f6 }
    footer { font-size:.875rem;color:#6c757d }
    /* dark mode tweak for GitHub */
    @media (prefers-color-scheme: dark) {
      body { background:#0d1117;color:#c9d1d9 }
      .hero { background:#1f6feb }
    }
  </style>
</head>
<body>

<!-- ­­­­­­­­­­­­­­­­­­­­­­­ Hero ­­­­­­­­­­­­­­­­­­­­­­­ -->
<section class="hero text-center py-5">
  <div class="container">
    <h1 class="display-4 mb-3">Q-pot 💶🤖</h1>
    <p class="lead mb-4">
      AI-powered <strong>financial coach</strong> for Bunq users.<br>
      Analyse spending, set goals, optimise investments &mdash; all in one chat.
    </p>
    <a href="#quickstart" class="btn btn-light btn-lg fw-semibold">
      🚀 Get Started
    </a>
  </div>
</section>

<!-- ­­­­­­­­­­­­­­­­­­­­­­­ Features ­­­­­­­­­­­­­­­­­­­­­­­ -->
<section class="py-5">
  <div class="container">
    <h2 class="mb-4 text-center">Key Features</h2>
    <div class="row g-4">
      <div class="col-md-6 col-lg-4">
        <div class="d-flex align-items-start">
          <div class="me-3 feature-icon">🧠</div>
          <div>
            <h5>LLM-driven Advice</h5>
            <p class="mb-0">OpenAI GPT-4o generates clear, actionable
               recommendations with Markdown formatting.</p>
          </div>
        </div>
      </div>
      <div class="col-md-6 col-lg-4">
        <div class="d-flex align-items-start">
          <div class="me-3 feature-icon">🔌</div>
          <div>
            <h5>MCP Tool-Calls</h5>
            <p class="mb-0">Bridges Chat GPT ↔ Bunq-style tools
               (<code>get_accounts</code>, <code>search</code>, etc.).</p>
          </div>
        </div>
      </div>
      <div class="col-md-6 col-lg-4">
        <div class="d-flex align-items-start">
          <div class="me-3 feature-icon">🌐</div>
          <div>
            <h5>DuckDuckGo Search</h5>
            <p class="mb-0">Pulls external facts to support advice, tolerant
               of strict TLS proxies.</p>
          </div>
        </div>
      </div>
      <div class="col-md-6 col-lg-4">
        <div class="d-flex align-items-start">
          <div class="me-3 feature-icon">💸</div>
          <div>
            <h5>Mortgage &amp; Investments</h5>
            <p class="mb-0">Mock tools for mortgage transactions and portfolio
               performance&mdash;ready for real data.</p>
          </div>
        </div>
      </div>
      <div class="col-md-6 col-lg-4">
        <div class="d-flex align-items-start">
          <div class="me-3 feature-icon">⚡</div>
          <div>
            <h5>Single Docker Image</h5>
            <p class="mb-0">UI, FastAPI gateway, MCP client &amp; server all in
               one slim container.</p>
          </div>
        </div>
      </div>
      <div class="col-md-6 col-lg-4">
        <div class="d-flex align-items-start">
          <div class="me-3 feature-icon">☁️</div>
          <div>
            <h5>Cloud-Ready</h5>
            <p class="mb-0">Deploy to Cloud Run, Render, Fly.io or any container host in minutes.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ­­­­­­­­­­­­­­­­­­­­­­­ Architecture Summary ­­­­­­­­­­­­­­­­­­­­­­­ -->
<section class="py-5 bg-light border-top">
  <div class="container">
    <h2 class="mb-4 text-center">Architecture at a Glance</h2>
    <div class="table-responsive">
      <table class="table align-middle">
        <thead class="table-light">
          <tr><th scope="col">Layer / File</th><th scope="col">Tech / Purpose</th></tr>
        </thead>
        <tbody>
          <tr><td><code>chat_web/index.html</code></td><td>Static SPA (vanilla JS), Font-Awesome icons, scrollable chat</td></tr>
          <tr><td><code>chat_web/app.py</code></td><td>FastAPI server – serves UI + REST endpoints <code>/chat</code>, <code>/user_info</code></td></tr>
          <tr><td><code>bunq_mcp_client.py</code></td><td>Bridges OpenAI Chat ↔ MCP servers, manages tool-calls</td></tr>
          <tr><td><code>bunq_mcp_server.py</code></td><td>Mock Bunq tools, web-search, mortgage and portfolio data</td></tr>
          <tr><td><code>Dockerfile</code></td><td>Slim Python 3.12 image; runs <code>uvicorn chat_web.app:app</code> (port 8000)</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<!-- ­­­­­­­­­­­­­­­­­­­­­­­ Quick Start ­­­­­­­­­­­­­­­­­­­­­­­ -->
<section class="py-5" id="quickstart">
  <div class="container">
    <h2 class="mb-4 text-center">Quick Start</h2>
    <pre class="bg-dark text-white p-3 rounded">
git clone https://github.com/your-org/q-pot.git
cd q-pot

cp .env.example .env     # add your OPENAI_API_KEY
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt

uvicorn chat_web.app:app --reload
# → open http://localhost:8000
    </pre>
  </div>
</section>

<!-- ­­­­­­­­­­­­­­­­­­­­­­­ Docker ­­­­­­­­­­­­­­­­­­­­­­­ -->
<section class="py-5 bg-light border-top">
  <div class="container">
    <h2 class="mb-4 text-center">Docker Usage</h2>
    <pre class="bg-dark text-white p-3 rounded">
# Build
docker build -t qpot:latest .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e BUNQ_API_KEY=dummy \
  qpot
    </pre>
  </div>
</section>

<!-- ­­­­­­­­­­­­­­­­­­­­­­­ Env Vars ­­­­­­­­­­­­­­­­­­­­­­­ -->
<section class="py-5">
  <div class="container">
    <h2 class="mb-4 text-center">Environment Variables</h2>
    <div class="table-responsive">
      <table class="table table-striped align-middle">
        <thead class="table-light">
          <tr><th>Variable</th><th>Description</th><th>Required</th></tr>
        </thead>
        <tbody>
          <tr><td><code>OPENAI_API_KEY</code></td><td>Secret key for Chat Completions</td><td>✅</td></tr>
          <tr><td><code>BUNQ_API_KEY</code></td><td>Real or mock Bunq key (demo uses dummy)</td><td></td></tr>
          <tr><td><code>BUNQ_ENVIRONMENT</code></td><td><code>PRODUCTION</code> or <code>SANDBOX</code></td><td></td></tr>
          <tr><td><code>MCP_SERVER_COMMAND</code></td><td>Override path/args for MCP server</td><td></td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<!-- ­­­­­­­­­­­­­­­­­­­­­­­ Footer ­­­­­­­­­­­­­­­­­­­­­­­ -->
<footer class="py-4 border-top">
  <div class="container text-center">
    <p class="mb-2">MIT License – do what you like, no warranty.</p>
    <p class="mb-0">© 2025 Q-pot / FinCoach Team</p>
  </div>
</footer>

</body>
</html>