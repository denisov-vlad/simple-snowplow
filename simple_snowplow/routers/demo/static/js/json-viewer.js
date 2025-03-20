/**
 * JSONViewer - Tree-based JSON viewer for better JSON visualization
 */
class JSONViewer {
    constructor(options = {}) {
        this.expanded = options.expanded || false;
        this.withQuotes = options.withQuotes !== undefined ? options.withQuotes : true;
        this.withLinks = options.withLinks || false;
        this.container = document.createElement('div');
        this.container.className = 'json-viewer';
        
        if (options.maxHeight) {
            this.container.style.maxHeight = options.maxHeight;
        }
    }
    
    getContainer() {
        return this.container;
    }
    
    showJSON(json, parentKey = null, isLast = true) {
        this.container.innerHTML = '';
        
        // Add toolbar with expand/collapse all buttons
        const toolbar = document.createElement('div');
        toolbar.className = 'json-toolbar';
        
        const expandBtn = document.createElement('button');
        expandBtn.textContent = 'Expand All';
        expandBtn.onclick = () => this._toggleAll(true);
        
        const collapseBtn = document.createElement('button');
        collapseBtn.textContent = 'Collapse All';
        collapseBtn.onclick = () => this._toggleAll(false);
        
        toolbar.appendChild(expandBtn);
        toolbar.appendChild(collapseBtn);
        this.container.appendChild(toolbar);
        
        // Add copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-button';
        copyBtn.textContent = 'Copy';
        copyBtn.onclick = () => {
            try {
                navigator.clipboard.writeText(JSON.stringify(json, null, 2))
                    .then(() => {
                        copyBtn.textContent = 'Copied!';
                        setTimeout(() => copyBtn.textContent = 'Copy', 1000);
                    });
            } catch (err) {
                console.error('Failed to copy: ', err);
            }
        };
        this.container.appendChild(copyBtn);
        
        // Format and append the JSON
        this._createNode(this.container, json, parentKey, isLast);
        return this;
    }
    
    _createNode(parent, value, key, isLast) {
        const type = this._getType(value);
        const isObject = type === 'object' || type === 'array';
        
        // Create line element
        const line = document.createElement('div');
        line.className = 'line';
        
        // Add expand/collapse caret if it's an object or array
        if (isObject && Object.keys(value).length) {
            const caretIcon = document.createElement('div');
            caretIcon.className = `caret-icon ${this.expanded ? 'expanded' : 'collapsed'}`;
            caretIcon.onclick = (e) => {
                e.stopPropagation();
                const isExpanded = caretIcon.classList.toggle('expanded');
                caretIcon.classList.toggle('collapsed', !isExpanded);
                
                const jsonChildren = line.nextElementSibling;
                if (jsonChildren) {
                    jsonChildren.classList.toggle('hidden', !isExpanded);
                }
            };
            line.appendChild(caretIcon);
        } else {
            // Empty space to maintain alignment
            const emptyIcon = document.createElement('div');
            emptyIcon.className = 'empty-icon';
            line.appendChild(emptyIcon);
        }
        
        // Add key if available
        if (key !== null) {
            const keyElement = document.createElement('span');
            keyElement.className = 'json-key';
            keyElement.textContent = this.withQuotes ? `"${key}":` : `${key}:`;
            line.appendChild(keyElement);
        }
        
        // Add brackets and braces for objects and arrays
        if (isObject) {
            const openBrace = document.createElement('span');
            openBrace.className = 'json-brace';
            openBrace.textContent = type === 'object' ? '{' : '[';
            line.appendChild(openBrace);
            
            // Show object size
            const size = Object.keys(value).length;
            if (size > 0) {
                const sizeIndicator = document.createElement('span');
                sizeIndicator.className = 'json-literal json-literal-number';
                sizeIndicator.textContent = ` // ${size} ${size === 1 ? 'item' : 'items'}`;
                line.appendChild(sizeIndicator);
            }
            
            parent.appendChild(line);
            
            // Create children container
            const children = document.createElement('div');
            children.className = `json-indent ${this.expanded ? '' : 'hidden'}`;
            
            // Process all the object children
            const entries = Object.entries(value);
            entries.forEach(([childKey, childValue], index) => {
                this._createNode(children, childValue, childKey, index === entries.length - 1);
            });
            
            parent.appendChild(children);
            
            // Create closing braces
            const lineEnd = document.createElement('div');
            lineEnd.className = 'line';
            
            const emptyIcon = document.createElement('div');
            emptyIcon.className = 'empty-icon';
            lineEnd.appendChild(emptyIcon);
            
            const closeBrace = document.createElement('span');
            closeBrace.className = 'json-brace';
            closeBrace.textContent = type === 'object' ? '}' : ']';
            lineEnd.appendChild(closeBrace);
            
            if (!isLast) {
                const comma = document.createElement('span');
                comma.textContent = ',';
                lineEnd.appendChild(comma);
            }
            
            parent.appendChild(lineEnd);
        } else {
            // For primitives, just add the formatted value
            const valueElement = this._createSimpleNode(value);
            line.appendChild(valueElement);
            
            if (!isLast) {
                const comma = document.createElement('span');
                comma.textContent = ',';
                line.appendChild(comma);
            }
            
            parent.appendChild(line);
        }
    }
    
    _createSimpleNode(value) {
        const type = this._getType(value);
        const valueElement = document.createElement('span');
        let valueClass = 'json-literal';
        let valueContent = String(value);
        
        switch (type) {
            case 'string':
                valueClass = 'json-string';
                valueContent = this.withQuotes ? `"${valueContent}"` : valueContent;
                
                // Convert links to anchors if enabled
                if (this.withLinks && this._isURL(value)) {
                    const link = document.createElement('a');
                    link.href = value;
                    link.target = '_blank';
                    link.textContent = valueContent;
                    link.className = valueClass;
                    return link;
                }
                break;
            case 'number':
                valueClass = 'json-literal-number';
                break;
            case 'boolean':
                valueClass = 'json-literal-boolean';
                break;
            case 'null':
                valueClass = 'json-literal-null';
                valueContent = 'null';
                break;
            case 'undefined':
                valueClass = 'json-literal-null';
                valueContent = 'undefined';
                break;
        }
        
        valueElement.className = valueClass;
        valueElement.textContent = valueContent;
        return valueElement;
    }
    
    _getType(value) {
        if (value === null) return 'null';
        if (value === undefined) return 'undefined';
        
        if (Array.isArray(value)) return 'array';
        if (typeof value === 'object') return 'object';
        
        return typeof value;
    }
    
    _isURL(str) {
        try {
            new URL(str);
            return true;
        } catch (e) {
            return false;
        }
    }
    
    _toggleAll(expand) {
        const carets = this.container.querySelectorAll('.caret-icon');
        const jsonIndents = this.container.querySelectorAll('.json-indent');
        
        carets.forEach(caret => {
            caret.classList.toggle('expanded', expand);
            caret.classList.toggle('collapsed', !expand);
        });
        
        jsonIndents.forEach(indent => {
            indent.classList.toggle('hidden', !expand);
        });
    }
} 