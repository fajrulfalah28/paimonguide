<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description"
        content="Paimon Guide — An intelligent chatbot for Genshin Impact quest prerequisites. Powered by NER and CRF algorithms.">
    <title>Paimon Guide — Quest Prerequisite Chatbot</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    @vite(['resources/css/app.css', 'resources/js/app.js'])
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        @font-face {
            font-family: 'HYWenHei';
            src: url('{{ asset('fonts/zhcn.ttf') }}') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }
    </style>
</head>

<body>
    <div id="app-loader" class="app-loader">
        <div class="loader-content">
            <img src="/images/paimon-logo.webp" alt="Loading..." class="loader-logo">
            <div class="loader-spinner"></div>
            <div class="loader-text">The best travel companion ever!</div>
        </div>
    </div>

    <div class="app-layout" id="app">


        <div class="mobile-topbar">
            <button class="mobile-menu-btn mobile-info-btn" id="btn-open-left" aria-label="Open info sidebar">
                <i class="fa-solid fa-circle-info"></i>
            </button>
            <span class="mobile-topbar-title">✦ Paimon Guide ✦</span>
            <button class="mobile-menu-btn" id="btn-open-right" aria-label="Open settings sidebar">
                <span></span><span></span><span></span>
            </button>
        </div>


        <div class="drawer-backdrop" id="drawer-backdrop"></div>

        <aside class="sidebar-left">
            <div class="sidebar-left-inner">
                <div class="sidebar-left-content">
                    <div class="logo-section">
                        <img src="/images/paimon-logo.webp" alt="Paimon Guide Logo" class="logo-image">
                        <div class="logo-card-wrapper">
                            <div class="logo-wing logo-wing--left">
                                <img src="/images/banner-wing-left.svg" alt="">
                            </div>
                            <div class="logo-card">
                                <div class="logo-title">
                                    Paimon<br>Guide
                                </div>
                                <div class="logo-subtitle">Version 1.0 - By Faun</div>
                            </div>
                            <div class="logo-wing logo-wing--right">
                                <img src="/images/banner-wing-right.svg" alt="">
                            </div>
                        </div>
                    </div>

                    <div class="about-section">
                        <div class="section-title">About The Tools</div>
                        <div class="about-card">
                            <div class="about-text">
                                <strong>Paimon Guide</strong> is an intelligent chatbot prototype designed to identify
                                in-game quest prerequisites.
                                <br><br>
                                This system is powered by Natural Language Processing, utilizing Named Entity
                                Recognition (NER) and Conditional Random Field (CRF) algorithms to accurately extract
                                information from your queries.
                            </div>
                        </div>
                    </div>

                    <div class="links-section">
                        <div class="section-title">Know more about me!</div>
                        <div class="links-container">
                            <a href="https://github.com/fajrulfalah28" target="_blank" rel="noopener noreferrer"
                                class="link-button link-button--github" id="btn-github">Github</a>
                            <a href="https://discordapp.com/users/428859474862931970" target="_blank"
                                rel="noopener noreferrer" class="link-button link-button--discord"
                                id="btn-discord">Discord</a>
                        </div>
                    </div>

                </div>

                <div class="sidebar-footer">Assets by © Cognosphere</div>
            </div>
        </aside>

        <main class="chat-panel">
            <div class="chat-messages" id="chat-messages">
            </div>

            <div class="chat-input-section">
                <input type="text" id="chat-input" class="chat-input" placeholder="Ask your question here!"
                    autocomplete="off" maxlength="500">
                <button type="button" id="send-btn" class="chat-send-btn">Send</button>
            </div>
        </main>

        <aside class="sidebar-right">
            <div class="sidebar-right-inner">
                <div class="sidebar-right-content">

                    {{-- Nickname --}}
                    <div class="nickname-section">
                        <div class="section-title">Your Nickname</div>
                        <input type="text" id="nickname-input" class="nickname-input" placeholder="Enter nickname..."
                            maxlength="30" value="Traveler">
                    </div>

                    <div class="avatar-section">
                        <div class="section-title">Avatar Selector</div>
                        <div class="avatar-grid" id="avatar-grid">
                        </div>
                    </div>

                </div>

                <div class="paimon-decoration">
                    <img src="/images/paimon-decoration.webp" alt="Paimon">
                </div>
            </div>
        </aside>

    </div>
</body>

</html>