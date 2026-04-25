/**
 * Apple Search Panel - Apple.com Style
 * 搜索面板交互逻辑
 */

(function() {
    'use strict';

    // 状态管理
    const state = {
        isOpen: false,
        searchTimer: null,
        currentQuery: '',
        highlightedIndex: -1,
        suggestions: [],
        isLoading: false
    };

    // 配置
    const config = {
        debounceDelay: 150,      // 输入防抖延迟
        minQueryLength: 0,        // 开始搜索的最小字符数
        maxSuggestions: 6,        // 最大建议数量
        maxQuickLinks: 6          // 最大快捷链接数量
    };

    // DOM 元素
    let searchPanel = null;
    let searchOverlay = null;
    let searchInput = null;
    let clearBtn = null;
    let closeBtn = null;
    let resultsContainer = null;

    // 搜索建议数据（可从后端获取）
    const quickLinks = [
        {
            text: '耳机',
            subtext: '降噪耳机 · 无线耳机',
            icon: '🎧',
            url: '/products?category=耳机'
        },
        {
            text: '音响',
            subtext: '蓝牙音响 · Hi-Fi',
            icon: '🔊',
            url: '/products?category=音响'
        },
        {
            text: 'Sony',
            subtext: 'WH-1000XM5',
            icon: 'Sony',
            url: '/products?brand=Sony'
        },
        {
            text: 'Bose',
            subtext: 'QuietComfort 系列',
            icon: 'Bose',
            url: '/products?brand=Bose'
        },
        {
            text: '母亲节',
            subtext: '精选礼物',
            icon: '🎁',
            url: '/mothers-day'
        },
        {
            text: '配件',
            subtext: '耳机垫 · 线材',
            icon: '📦',
            url: '/products?category=配件'
        }
    ];

    /**
     * 初始化搜索功能
     */
    function init() {
        createSearchPanel();
        bindEvents();
    }

    /**
     * 创建搜索面板 DOM
     */
    function createSearchPanel() {
        // 创建遮罩层
        searchOverlay = document.createElement('div');
        searchOverlay.className = 'search-panel-overlay';
        searchOverlay.id = 'searchPanelOverlay';
        searchOverlay.onclick = closeSearchPanel;
        document.body.appendChild(searchOverlay);

        // 创建搜索面板
        searchPanel = document.createElement('div');
        searchPanel.className = 'search-panel';
        searchPanel.id = 'searchPanel';
        searchPanel.innerHTML = `
            <div class="search-panel-content">
                <div class="search-input-row">
                    <svg class="search-input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="M21 21l-4.35-4.35"/>
                    </svg>
                    <div class="search-input-wrapper">
                        <input type="text"
                               id="searchInput"
                               placeholder="搜索产品、品牌或分类..."
                               autocomplete="off"
                               autocorrect="off"
                               autocapitalize="off"
                               spellcheck="false">
                        <button class="search-clear-btn" id="searchClearBtn" title="清除">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 6L6 18M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <button class="search-close-btn" id="searchCloseBtn" title="关闭">
                        取消
                    </button>
                </div>

                <div class="search-results-container" id="searchResultsContainer">
                    <!-- 动态内容 -->
                </div>
            </div>
        `;
        document.body.appendChild(searchPanel);

        // 获取 DOM 引用
        searchInput = document.getElementById('searchInput');
        clearBtn = document.getElementById('searchClearBtn');
        closeBtn = document.getElementById('searchCloseBtn');
        resultsContainer = document.getElementById('searchResultsContainer');

        // 初始显示快捷链接
        renderQuickLinks();
    }

    /**
     * 绑定事件
     */
    function bindEvents() {
        // 搜索触发按钮
        const searchBtns = document.querySelectorAll('.nav-search-btn, .nav-link[data-search]');
        searchBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                openSearchPanel();
            });
        });

        // 关闭按钮
        closeBtn.addEventListener('click', closeSearchPanel);

        // 清除按钮
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            clearBtn.classList.remove('visible');
            searchInput.focus();
            renderQuickLinks();
        });

        // 输入事件
        searchInput.addEventListener('input', debounce(handleSearchInput, config.debounceDelay));

        // 键盘事件
        searchInput.addEventListener('keydown', handleKeydown);

        // ESC 关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && state.isOpen) {
                closeSearchPanel();
            }
        });

        // 窗口 resize
        window.addEventListener('resize', debounce(() => {
            if (state.isOpen) {
                // 移动端全屏体验
                if (window.innerWidth <= 768) {
                    searchPanel.style.top = '0';
                    searchPanel.style.height = '100vh';
                }
            }
        }, 100));
    }

    /**
     * 打开搜索面板
     */
    function openSearchPanel() {
        state.isOpen = true;
        searchOverlay.classList.add('visible');
        searchPanel.classList.remove('closing');
        searchPanel.classList.add('visible');

        // 移动端全屏
        if (window.innerWidth <= 768) {
            searchPanel.style.top = '0';
            searchPanel.style.height = '100vh';
        }

        // 聚焦输入框
        setTimeout(() => {
            searchInput.focus();
        }, 100);

        // 阻止背景滚动
        document.body.style.overflow = 'hidden';
    }

    /**
     * 关闭搜索面板
     */
    function closeSearchPanel() {
        state.isOpen = false;
        searchPanel.classList.add('closing');

        setTimeout(() => {
            searchOverlay.classList.remove('visible');
            searchPanel.classList.remove('visible');
            searchPanel.classList.remove('closing');
            searchPanel.style.top = '';
            searchPanel.style.height = '';
        }, 200);

        // 恢复背景滚动
        document.body.style.overflow = '';

        // 重置状态
        state.currentQuery = '';
        state.highlightedIndex = -1;
    }

    /**
     * 处理搜索输入
     */
    function handleSearchInput() {
        const query = searchInput.value.trim();

        // 显示/隐藏清除按钮
        if (query.length > 0) {
            clearBtn.classList.add('visible');
        } else {
            clearBtn.classList.remove('visible');
        }

        state.currentQuery = query;

        // 空查询显示快捷链接
        if (query.length < config.minQueryLength) {
            renderQuickLinks();
            return;
        }

        // 执行搜索
        performSearch(query);
    }

    /**
     * 执行搜索
     */
    async function performSearch(query) {
        state.isLoading = true;
        renderLoading();

        try {
            // 调用搜索 API
            const response = await fetch(`/api/search/suggestions?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            state.suggestions = data.suggestions || [];
            state.isLoading = false;

            if (state.suggestions.length > 0) {
                renderSuggestions(state.suggestions, query);
            } else {
                renderNoResults(query);
            }
        } catch (error) {
            state.isLoading = false;
            // 降级：显示"无结果"
            renderNoResults(query);
        }
    }

    /**
     * 渲染加载状态
     */
    function renderLoading() {
        resultsContainer.innerHTML = `
            <div class="search-loading">
                <div class="search-spinner"></div>
            </div>
        `;
    }

    /**
     * 渲染快捷链接
     */
    function renderQuickLinks() {
        const linksHtml = quickLinks.slice(0, config.maxQuickLinks).map(link => `
            <a href="${link.url}" class="search-quick-link">
                <div class="search-quick-link-icon">${link.icon}</div>
                <div>
                    <div class="search-quick-link-text">${link.text}</div>
                    <div class="search-quick-link-subtext">${link.subtext}</div>
                </div>
            </a>
        `).join('');

        resultsContainer.innerHTML = `
            <div class="search-section">
                <div class="search-section-title">热门搜索</div>
                <div class="search-quick-links">
                    ${linksHtml}
                </div>
            </div>
            <div class="search-keyboard-hint">
                <span class="search-key">↵</span>
                <span class="search-key-hint">选择</span>
                <span class="search-key">↑</span>
                <span class="search-key">↓</span>
                <span class="search-key-hint">导航</span>
                <span class="search-key">esc</span>
                <span class="search-key-hint">关闭</span>
            </div>
        `;

        state.highlightedIndex = -1;
    }

    /**
     * 渲染搜索建议
     */
    function renderSuggestions(suggestions, query) {
        const suggestionsHtml = suggestions.slice(0, config.maxSuggestions).map((item, index) => {
            // 高亮匹配的文字
            const highlightedName = highlightMatch(item.name, query);

            return `
                <li class="search-suggestion-item" data-index="${index}" data-url="${item.url}">
                    <div class="search-suggestion-icon">
                        ${item.image ? `<img src="${item.image}" alt="">` : `
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <circle cx="11" cy="11" r="8"/>
                                <path d="M21 21l-4.35-4.35"/>
                            </svg>
                        `}
                    </div>
                    <div class="search-suggestion-content">
                        <div class="search-suggestion-name">${highlightedName}</div>
                        ${item.brand ? `<div class="search-suggestion-meta">${item.brand} · ${item.category || ''}</div>` : ''}
                    </div>
                    ${item.price ? `<div class="search-suggestion-price">¥${item.price}</div>` : ''}
                    <svg class="search-suggestion-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M9 18l6-6-6-6"/>
                    </svg>
                </li>
            `;
        }).join('');

        resultsContainer.innerHTML = `
            <div class="search-section">
                <div class="search-section-title">产品建议</div>
                <ul class="search-suggestions">
                    ${suggestionsHtml}
                </ul>
            </div>
        `;

        // 绑定建议项点击事件
        const items = resultsContainer.querySelectorAll('.search-suggestion-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const url = item.dataset.url;
                window.location.href = url;
            });

            item.addEventListener('mouseenter', () => {
                setHighlight(index);
            });
        });

        state.highlightedIndex = -1;
    }

    /**
     * 渲染无结果状态
     */
    function renderNoResults(query) {
        resultsContainer.innerHTML = `
            <div class="search-no-results">
                <svg class="search-no-results-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="M21 21l-4.35-4.35"/>
                    <path d="M8 8l6 6M14 8l-6 6"/>
                </svg>
                <h3>未找到"${escapeHtml(query)}"的相关结果</h3>
                <p>试试其他关键词，或浏览我们的产品分类</p>
            </div>
            <div class="search-section" style="margin-top: 24px;">
                <div class="search-section-title">快捷链接</div>
                <div class="search-quick-links">
                    ${quickLinks.slice(0, 4).map(link => `
                        <a href="${link.url}" class="search-quick-link">
                            <div class="search-quick-link-icon">${link.icon}</div>
                            <div>
                                <div class="search-quick-link-text">${link.text}</div>
                            </div>
                        </a>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * 处理键盘导航
     */
    function handleKeydown(e) {
        const items = resultsContainer.querySelectorAll('.search-suggestion-item');
        const itemCount = items.length;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (itemCount > 0) {
                    const newIndex = state.highlightedIndex < itemCount - 1 ? state.highlightedIndex + 1 : 0;
                    setHighlight(newIndex);
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                if (itemCount > 0) {
                    const newIndex = state.highlightedIndex > 0 ? state.highlightedIndex - 1 : itemCount - 1;
                    setHighlight(newIndex);
                }
                break;

            case 'Enter':
                e.preventDefault();
                if (state.highlightedIndex >= 0 && items[state.highlightedIndex]) {
                    const url = items[state.highlightedIndex].dataset.url;
                    window.location.href = url;
                } else if (state.currentQuery) {
                    // 跳转到搜索结果页
                    window.location.href = `/search?q=${encodeURIComponent(state.currentQuery)}`;
                }
                break;
        }
    }

    /**
     * 设置高亮项
     */
    function setHighlight(index) {
        const items = resultsContainer.querySelectorAll('.search-suggestion-item');

        items.forEach((item, i) => {
            if (i === index) {
                item.classList.add('highlighted');
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                item.classList.remove('highlighted');
            }
        });

        state.highlightedIndex = index;
    }

    /**
     * 高亮匹配文字
     */
    function highlightMatch(text, query) {
        if (!query) return escapeHtml(text);

        const escapedText = escapeHtml(text);
        const escapedQuery = escapeHtml(query);

        const regex = new RegExp(`(${query})`, 'gi');
        return escapedText.replace(regex, '<mark>$1</mark>');
    }

    /**
     * HTML 转义
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 防抖函数
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // DOM 加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 暴露全局方法
    window.AppleSearch = {
        open: openSearchPanel,
        close: closeSearchPanel
    };

})();
