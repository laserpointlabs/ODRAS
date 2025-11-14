# Workbench Visibility Control Pattern

## Overview

This document describes the standardized pattern for showing/hiding workbenches in ODRAS. All workbench visibility is controlled through a single, centralized function.

## Core Function: `switchWorkbench(workbenchId)`

**Location**: `frontend/js/core/workbench-manager.js`

**Purpose**: Central function that controls all workbench visibility. This is the ONLY function that should be used to show/hide workbenches.

### How It Works

1. **Updates Icon Bar**: Removes `active` class from all icons, adds to selected icon
2. **Hides All Workbenches**: Removes `active` class from all `.workbench` elements
3. **Shows Selected Workbench**: Adds `active` class to target workbench (`#wb-{workbenchId}`)
4. **Initializes Workbench**: Calls workbench-specific initialization if needed
5. **Persists State**: Saves to localStorage and updates URL

### CSS Rules

```css
/* All workbenches are hidden by default */
.workbench {
  display: none;
}

/* Active workbench is shown */
.workbench.active {
  display: flex;
}
```

## Adding a New Workbench

### Step 1: Add HTML Structure

In `frontend/index.html`, add a workbench section:

```html
<section id="wb-{workbenchId}" class="workbench">
  <!-- Your workbench content here -->
</section>
```

### Step 2: Add Icon to Sidebar

In `frontend/index.html`, add an icon:

```html
<div class="icon" data-wb="{workbenchId}" title="Workbench Name">
  <!-- SVG icon -->
</div>
```

### Step 3: Add Initialization Logic (Optional)

In `frontend/js/core/workbench-manager.js`, add initialization in `switchWorkbench()`:

```javascript
} else if (workbenchId === 'your-workbench') {
  // Initialize your workbench
  import('/static/js/workbenches/your-workbench/your-workbench-ui.js')
    .then(module => {
      if (module.initializeYourWorkbench) {
        module.initializeYourWorkbench();
      }
    })
    .catch(err => console.warn('Could not load workbench:', err));
}
```

### Step 4: Create Workbench Module (Optional)

Create `frontend/js/workbenches/your-workbench/your-workbench-ui.js`:

```javascript
export function initializeYourWorkbench() {
  console.log('🔷 Initializing Your Workbench...');
  // Your initialization code
}
```

## Initialization Flow

1. **Page Load**: `initializeWorkbenchManager()` is called
2. **Default Workbench**: `initializeDefaultWorkbench()` determines which workbench to show:
   - Checks URL parameter (`?wb=ontology`)
   - Checks localStorage (`active_workbench`)
   - Checks HTML (`class="workbench active"`)
   - Falls back to `'ontology'`
3. **Switch**: Calls `switchWorkbench()` with determined workbench
4. **After Login**: `showMainView()` also activates default workbench

## Testing Workbench Visibility

### In Tests

```python
# Wait for workbench to be visible
page.wait_for_selector("#wb-ontology.workbench.active", timeout=10000)

# Check visibility
expect(page.locator("#wb-ontology.workbench.active")).to_be_visible()
```

### In Browser Console

```javascript
// Switch to a workbench
import('/static/js/core/workbench-manager.js').then(m => m.switchWorkbench('ontology'));

// Check current workbench
document.querySelector('.workbench.active')?.id
```

## Common Patterns

### Programmatic Workbench Switch

```javascript
import { switchWorkbench } from '/static/js/core/workbench-manager.js';
switchWorkbench('requirements');
```

### Event-Based Switch

```javascript
import { emitEvent } from '/static/js/core/event-bus.js';
emitEvent('workbench:switch', { workbench: 'ontology' });
```

### Check Current Workbench

```javascript
const activeWorkbench = document.querySelector('.workbench.active')?.id.replace('wb-', '');
console.log('Current workbench:', activeWorkbench);
```

## Troubleshooting

### Workbench Not Showing

1. **Check CSS**: Ensure `.workbench.active { display: flex; }` exists
2. **Check HTML**: Ensure workbench has `id="wb-{workbenchId}"`
3. **Check Function**: Ensure `switchWorkbench()` is being called
4. **Check Console**: Look for errors in browser console

### Multiple Workbenches Showing

- Ensure `switchWorkbench()` removes `active` from all workbenches before adding to target
- Check for CSS conflicts or inline styles

### Workbench Not Initializing

- Check that initialization code is in `switchWorkbench()` for your workbench
- Verify module import path is correct
- Check browser console for import errors

## Best Practices

1. **Always use `switchWorkbench()`**: Never manually add/remove `active` class
2. **Centralize initialization**: Put all workbench init logic in `switchWorkbench()`
3. **Use events**: Emit `workbench:switched` event for other modules to react
4. **Persist state**: Always save to localStorage and URL
5. **Test visibility**: Ensure tests wait for proper visibility before assertions

---

**Last Updated**: 2025-01-XX  
**Maintainer**: Frontend Team
