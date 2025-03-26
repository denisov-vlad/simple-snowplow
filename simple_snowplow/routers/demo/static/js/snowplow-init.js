/**
 * Snowplow Tracker Initialization
 */

// Initialize Snowplow tracker
;(function(p,l,o,w,i,n,g){if(!p[i]){p.GlobalSnowplowNamespace=p.GlobalSnowplowNamespace||[]; p.GlobalSnowplowNamespace.push(i);p[i]=function(){(p[i].q=p[i].q||[]).push(arguments) };p[i].q=p[i].q||[];n=l.createElement(o);g=l.getElementsByTagName(o)[0];n.async=1; n.src=w;g.parentNode.insertBefore(n,g)}}(window,document,"script","http://127.0.0.1:8000/static/sp.js","snowplow"));

// Configure the tracker
window.snowplow('newTracker', 'sp1', 'http://127.0.0.1:8000', {
    appId: 'example',
    postPath: '/tracker',
    encodeBase64: false,
    discoverRootDomain: true,
    onRequestSuccess: requestCallback, // Callback defined in logger.js
    contexts: {
        webPage: true,
        session: true,
        browser: true,
        performanceNavigationTiming: true,
        performanceTiming: true,
        gaCookies: true,
        geolocation: false,
        clientHints: true,
    }
});

// Set user ID
window.snowplow('setUserId', 'test@email.com');

// Enable activity tracking
window.snowplow('enableActivityTracking', {
    minimumVisitLength: 5,
    heartbeatDelay: 5
});

// Enable link click tracking
window.snowplow('enableLinkClickTracking', {
    pseudoClicks: true,
    trackContent: true
});

// Add global contexts
let pageContext = {
    schema: "iglu:dev.snowplow.simple/page_data",
    data: {
        "id": "qwe123",
        "type": "main",
        "section": null
    }
};

let userContext = {
    schema: "iglu:dev.snowplow.simple/user_data",
    data: {
        "name": "John",
        "type": "contributor"
    }
};

window.snowplow('addGlobalContexts', [pageContext, userContext]);

// Initialize page tracking when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Track page view on load
    window.snowplow('trackPageView');

    // Initialize UI components
    initUI();
});
