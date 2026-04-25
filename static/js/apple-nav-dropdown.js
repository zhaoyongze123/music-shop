/**
 * Apple Navigation Dropdown - Apple.com Style
 * 导航栏悬停下拉菜单交互逻辑
 */

(function() {
    'use strict';

    // 状态管理
    const state = {
        activeDropdown: null,
        hoverTimer: null,
        leaveTimer: null,
        isTransitioning: false
    };

    // 配置
    const config = {
        hoverDelay: 300,      // 鼠标悬停触发延迟
        leaveDelay: 200,       // 鼠标离开关闭延迟
        animationDuration: 350 // 动画时长
    };

    // DOM 元素
    let overlay = null;
    let pageOverlay = null;

    /**
     * 初始化导航下拉功能
     */
    function init() {
        createOverlayElements();
        bindEvents();
        setupResponsiveBehavior();
    }

    /**
     * 创建遮罩层元素
     */
    function createOverlayElements() {
        // 创建主遮罩层
        overlay = document.createElement('div');
        overlay.className = 'nav-dropdown-overlay';
        overlay.id = 'navDropdownOverlay';
        document.body.appendChild(overlay);

        // 创建页面内容遮罩层
        pageOverlay = document.createElement('div');
        pageOverlay.className = 'page-content-overlay';
        pageOverlay.id = 'pageContentOverlay';
        document.body.appendChild(pageOverlay);
    }

    /**
     * 绑定事件
     */
    function bindEvents() {
        const navItems = document.querySelectorAll('.nav-item-wrapper[data-dropdown]');

        navItems.forEach(item => {
            const dropdownId = item.dataset.dropdown;
            const panel = document.getElementById(dropdownId);

            if (!panel) return;

            // 鼠标进入导航项
            item.addEventListener('mouseenter', (e) => handleNavEnter(e, item, panel));

            // 鼠标离开导航项
            item.addEventListener('mouseleave', (e) => handleNavLeave(e, item, panel));

            // 鼠标进入下拉面板
            panel.addEventListener('mouseenter', () => handlePanelEnter(item, panel));

            // 鼠标离开下拉面板
            panel.addEventListener('mouseleave', (e) => handlePanelLeave(e, item, panel));
        });

        // 点击遮罩关闭
        overlay.addEventListener('click', closeAllDropdowns);

        // ESC 键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeAllDropdowns();
            }
        });

        // 窗口 resize 时检查
        window.addEventListener('resize', debounce(handleResize, 150));
    }

    /**
     * 处理导航项鼠标进入
     */
    function handleNavEnter(e, navItem, panel) {
        // 清除之前的定时器
        clearTimeout(state.leaveTimer);
        clearTimeout(state.hoverTimer);

        // 如果当前有打开的下拉菜单但不是这个，快速切换
        if (state.activeDropdown && state.activeDropdown !== panel) {
            closeDropdown(state.activeDropdown, false); // 不等待，直接关闭
        }

        // 如果已经打开这个下拉，跳过
        if (state.activeDropdown === panel && panel.classList.contains('visible')) {
            return;
        }

        // 延迟打开
        state.hoverTimer = setTimeout(() => {
            openDropdown(panel, navItem);
        }, config.hoverDelay);
    }

    /**
     * 处理导航项鼠标离开
     */
    function handleNavLeave(e, navItem, panel) {
        clearTimeout(state.hoverTimer);

        state.leaveTimer = setTimeout(() => {
            closeDropdown(panel);
        }, config.leaveDelay);
    }

    /**
     * 处理下拉面板鼠标进入
     */
    function handlePanelEnter(navItem, panel) {
        clearTimeout(state.leaveTimer);
        clearTimeout(state.hoverTimer);
    }

    /**
     * 处理下拉面板鼠标离开
     */
    function handlePanelLeave(e, navItem, panel) {
        // 检查是否真的离开了整个区域
        const relatedTarget = e.relatedTarget;
        if (relatedTarget && (panel.contains(relatedTarget) || navItem.contains(relatedTarget))) {
            return;
        }

        state.leaveTimer = setTimeout(() => {
            closeDropdown(panel);
        }, config.leaveDelay);
    }

    /**
     * 打开下拉菜单
     */
    function openDropdown(panel, navItem) {
        if (state.isTransitioning) return;

        state.isTransitioning = true;
        state.activeDropdown = panel;

        // 激活导航项
        document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
        const link = navItem.querySelector('.nav-link');
        if (link) link.classList.add('active');

        // 显示遮罩
        overlay.classList.add('visible');
        pageOverlay.classList.add('active');

        // 显示面板
        panel.classList.remove('closing');
        panel.classList.add('visible');

        // 重置列动画
        const columns = panel.querySelectorAll('.dropdown-column');
        columns.forEach(col => {
            col.style.opacity = '0';
            col.style.transform = 'translateY(8px)';
        });

        // 触发重绘
        panel.offsetHeight;

        // 交错动画进入
        columns.forEach((col, index) => {
            setTimeout(() => {
                col.style.opacity = '1';
                col.style.transform = 'translateY(0)';
            }, index * 50);
        });

        setTimeout(() => {
            state.isTransitioning = false;
        }, config.animationDuration);
    }

    /**
     * 关闭下拉菜单
     */
    function closeDropdown(panel, animated = true) {
        if (!panel || !panel.classList.contains('visible')) return;

        if (animated) {
            panel.classList.add('closing');
            setTimeout(() => {
                hideDropdown(panel);
            }, 250); // 关闭动画时长
        } else {
            hideDropdown(panel);
        }
    }

    /**
     * 隐藏下拉菜单（实际移除可见状态）
     */
    function hideDropdown(panel) {
        panel.classList.remove('visible');
        panel.classList.remove('closing');

        // 隐藏遮罩
        overlay.classList.remove('visible');
        pageOverlay.classList.remove('active');

        // 移除导航项激活状态
        document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));

        if (state.activeDropdown === panel) {
            state.activeDropdown = null;
        }
    }

    /**
     * 关闭所有下拉菜单
     */
    function closeAllDropdowns() {
        clearTimeout(state.hoverTimer);
        clearTimeout(state.leaveTimer);

        const openPanels = document.querySelectorAll('.nav-dropdown-panel.visible');
        openPanels.forEach(panel => {
            closeDropdown(panel);
        });

        state.activeDropdown = null;
    }

    /**
     * 处理窗口尺寸变化
     */
    function handleResize() {
        // 移动端不需要下拉菜单行为
        if (window.innerWidth <= 1024) {
            closeAllDropdowns();
        }
    }

    /**
     * 设置响应式行为
     */
    function setupResponsiveBehavior() {
        // 移动端触摸支持
        const navItems = document.querySelectorAll('.nav-item-wrapper[data-dropdown]');

        navItems.forEach(item => {
            const dropdownId = item.dataset.dropdown;
            const panel = document.getElementById(dropdownId);
            const link = item.querySelector('.nav-link');

            if (!panel || !link) return;

            // 移动端点击展开
            link.addEventListener('click', (e) => {
                if (window.innerWidth <= 1024) {
                    e.preventDefault();
                    toggleMobileDropdown(panel, item);
                }
            });
        });
    }

    /**
     * 移动端下拉展开/收起
     */
    function toggleMobileDropdown(panel, navItem) {
        const isVisible = panel.classList.contains('visible');

        if (isVisible) {
            closeDropdown(panel);
        } else {
            openDropdown(panel, navItem);
        }
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

    // 暴露全局方法供外部调用
    window.AppleNavDropdown = {
        closeAll: closeAllDropdowns,
        open: function(dropdownId) {
            const panel = document.getElementById(dropdownId);
            const navItem = document.querySelector(`[data-dropdown="${dropdownId}"]`);
            if (panel && navItem) {
                openDropdown(panel, navItem);
            }
        }
    };

})();
