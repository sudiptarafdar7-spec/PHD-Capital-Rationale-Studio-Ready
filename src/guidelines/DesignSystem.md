# PHD Capital - Premium Design System v2.0

## 🎨 Overview
Ultra-premium design system with glassmorphism, translucency, enhanced typography, and smooth animations for both light and dark modes.

---

## 🌟 Key Features

### Premium Glassmorphism
- **Frosted glass effects** with backdrop blur
- **Translucent surfaces** for modern, layered UI
- **Subtle borders** with transparency
- **Depth through shadows** and blur

### Enhanced Typography
- **Inter font family** - Premium, clean typeface
- **Better font sizing** - Larger, more readable
- **Improved spacing** - Better line heights and letter spacing
- **Stronger hierarchy** - Bold headings, medium body

### Premium Animations
- **Smooth transitions** - Cubic bezier easing
- **Hover effects** - Subtle lifts and shadows
- **Focus glows** - Ring effects with glow
- **Active states** - Scale feedback

---

## 🎯 Core Classes

### Cards

#### Premium Card (Default)
Auto-applies glassmorphism with hover effects:
```tsx
<Card className="premium-card">
  {/* Translucent background, backdrop blur, hover lift */}
</Card>
```

#### Glass Card (Strong)
Stronger glass effect:
```tsx
<Card className="glass-card">
  {/* Enhanced blur and translucency */}
</Card>
```

#### Glass Strong
Maximum glassmorphism:
```tsx
<Card className="glass-strong">
  {/* Maximum blur and saturation */}
</Card>
```

#### Solid Card
No translucency (when needed):
```tsx
<Card className="solid-card">
  {/* Solid background, no blur */}
</Card>
```

### Dialogs & Popovers

All dialogs now have premium translucent backgrounds:
```tsx
<DialogContent className="glass-strong">
  {/* Auto-styled with backdrop blur and shadow */}
</DialogContent>
```

The overlay automatically has blur:
```tsx
{/* Overlay is automatically: bg-black/60 backdrop-blur-sm */}
```

---

## 🎨 Color System

### Semantic Colors

#### Primary (Blue)
Main brand color for CTAs and important actions:
```tsx
<Button className="bg-primary hover:bg-primary-hover">Action</Button>
<div className="icon-bg-primary"><Icon className="icon-primary" /></div>
```

#### Success (Green)
Completed states, success messages:
```tsx
<div className="icon-bg-success"><CheckCircle className="icon-success" /></div>
<Badge className="badge-success">Completed</Badge>
```

#### Warning (Amber)
Warnings, pending states:
```tsx
<div className="icon-bg-warning"><AlertTriangle className="icon-warning" /></div>
<Badge className="badge-warning">Pending</Badge>
```

#### Destructive/Danger (Red)
Errors, delete actions:
```tsx
<Button className="bg-destructive hover:bg-destructive-hover">Delete</Button>
<div className="icon-bg-danger"><XCircle className="icon-danger" /></div>
```

#### Info (Cyan)
Informational content:
```tsx
<div className="icon-bg-info"><Info className="icon-info" /></div>
<Badge className="badge-info">Processing</Badge>
```

#### Premium (Purple)
Special features, premium content:
```tsx
<Button className="bg-premium hover:bg-premium-hover">Upgrade</Button>
<div className="icon-bg-premium"><Star className="icon-premium" /></div>
```

---

## ✨ Glow Effects

### Button Glows
Buttons auto-have subtle glows matching their color:
```tsx
<Button>Primary</Button> {/* Auto primary glow */}
<Button variant="destructive">Delete</Button> {/* Auto destructive glow */}
```

### Icon Glows
Icon backgrounds have subtle glows:
```tsx
<div className="icon-bg-primary">  {/* Auto glow */}
  <FileText className="icon-primary" />
</div>
```

### Manual Glows
Apply glows manually:
```tsx
<Card className="glow-primary">Enhanced primary glow</Card>
<Card className="glow-success">Success glow</Card>
<Card className="glow-warning">Warning glow</Card>
<Card className="glow-danger">Danger glow</Card>
<Card className="glow-premium">Premium glow</Card>
```

---

## 🔘 Buttons

### Primary Button
```tsx
<Button className="bg-primary hover:bg-primary-hover text-white">
  Primary Action
</Button>
```

### Secondary Button
```tsx
<Button variant="secondary">
  Secondary Action
</Button>
```

### Outline Button
Translucent with border:
```tsx
<Button variant="outline" className="border-primary/50 text-primary hover:bg-primary hover:text-white">
  Outlined
</Button>
```

### Destructive Button
```tsx
<Button variant="destructive">
  Delete
</Button>
```

### Ghost Button
Minimal styling:
```tsx
<Button variant="ghost">
  Subtle Action
</Button>
```

### Sizes
```tsx
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>
<Button size="icon"><Icon /></Button>
```

---

## 📝 Inputs & Forms

### Input Fields
Auto-styled with focus glow:
```tsx
<Input 
  placeholder="Enter text"
  className="bg-input-background border-input"
/>
```

Features:
- Translucent background
- Hover border color change
- Focus glow effect (4px ring with color)
- Shadow on focus
- Smooth transitions

### With Label
```tsx
<div className="space-y-2">
  <Label>Field Name</Label>
  <Input />
</div>
```

---

## 🎭 Icons

### Icon Colors
```tsx
<CheckCircle className="icon-success" />
<AlertTriangle className="icon-warning" />
<XCircle className="icon-danger" />
<Info className="icon-info" />
<FileText className="icon-primary" />
<Star className="icon-premium" />
```

### Icon Backgrounds
Premium containers with glow:
```tsx
<div className="p-3 icon-bg-primary rounded-xl">
  <FileText className="w-6 h-6 icon-primary" />
</div>

<div className="p-3 icon-bg-success rounded-xl">
  <CheckCircle className="w-6 h-6 icon-success" />
</div>

<div className="p-3 icon-bg-warning rounded-xl">
  <AlertTriangle className="w-6 h-6 icon-warning" />
</div>

<div className="p-3 icon-bg-danger rounded-xl">
  <XCircle className="w-6 h-6 icon-danger" />
</div>

<div className="p-3 icon-bg-info rounded-xl">
  <Info className="w-6 h-6 icon-info" />
</div>

<div className="p-3 icon-bg-premium rounded-xl">
  <Star className="w-6 h-6 icon-premium" />
</div>
```

---

## 🏷️ Badges

Status badges with glows:
```tsx
<Badge className="badge-success">Completed</Badge>
<Badge className="badge-warning">Pending</Badge>
<Badge className="badge-danger">Failed</Badge>
<Badge className="badge-info">Processing</Badge>
<Badge className="badge-premium">Premium</Badge>
```

---

## 📢 Info Banners

### Primary Info
```tsx
<Card className="bg-primary-light border-primary/30 p-4">
  <div className="flex items-start gap-3">
    <div className="p-2 icon-bg-primary rounded-lg">
      <Info className="w-5 h-5 icon-primary" />
    </div>
    <div>
      <h3 className="text-primary mb-1">Title</h3>
      <p className="text-sm text-primary/80">Message</p>
    </div>
  </div>
</Card>
```

### Success Banner
```tsx
<Card className="bg-success-light border-success/30 p-4">
  <div className="flex items-start gap-3">
    <div className="p-2 icon-bg-success rounded-lg">
      <CheckCircle className="w-5 h-5 icon-success" />
    </div>
    <div>
      <h3 className="text-success mb-1">Success!</h3>
      <p className="text-sm text-success/80">Message</p>
    </div>
  </div>
</Card>
```

### Warning Banner
```tsx
<Card className="bg-warning-light border-warning/30 p-4">
  <div className="flex items-start gap-3">
    <div className="p-2 icon-bg-warning rounded-lg">
      <AlertTriangle className="w-5 h-5 icon-warning" />
    </div>
    <div>
      <h3 className="text-warning mb-1">Warning</h3>
      <p className="text-sm text-warning/80">Message</p>
    </div>
  </div>
</Card>
```

---

## 🎨 Gradients

### Gradient Backgrounds
```tsx
<div className="gradient-primary">Primary gradient</div>
<div className="gradient-premium">Premium gradient</div>
<div className="gradient-success">Success gradient</div>
```

### Text Gradients
```tsx
<h1 className="text-gradient-primary">Gradient Text</h1>
<h1 className="text-gradient-premium">Premium Gradient</h1>
```

---

## 📐 Typography

### Text Hierarchy
```tsx
<h1>Main Page Title</h1>        {/* 2rem, bold */}
<h2>Section Header</h2>           {/* 1.5rem, bold */}
<h3>Subsection</h3>               {/* 1.25rem, semibold */}
<h4>Minor Heading</h4>            {/* 1.125rem, semibold */}
<p>Body text</p>                  {/* 0.9375rem, normal */}
<label>Form Label</label>          {/* 0.875rem, medium */}
```

### Text Colors
```tsx
<p className="text-foreground">Primary text</p>
<p className="text-foreground-secondary">Secondary text</p>
<p className="text-muted-foreground">Muted text</p>
<p className="text-muted-foreground-light">Light muted text</p>
```

---

## 🎭 Transitions

### Smooth Transition
Default premium transition:
```tsx
<div className="transition-smooth">
  {/* 0.3s cubic-bezier transition */}
</div>
```

### Fast Transition
Quick feedback:
```tsx
<div className="transition-fast">
  {/* 0.15s cubic-bezier transition */}
</div>
```

---

## 🎯 Empty States

```tsx
<div className="border-2 border-dashed border-border rounded-xl p-10 text-center bg-muted/50">
  <Icon className="w-10 h-10 text-muted-foreground mx-auto mb-4" />
  <p className="text-foreground mb-1.5">No items found</p>
  <p className="text-sm text-muted-foreground">Create your first item</p>
</div>
```

---

## 🌓 Dark/Light Mode

All components auto-adapt! The design system includes:
- **Light Mode**: Gradient background, soft shadows, clean surfaces
- **Dark Mode**: Enhanced glassmorphism, stronger glows, deeper shadows

Toggle with:
```tsx
document.documentElement.classList.toggle('dark');
```

---

## ✅ Best Practices

1. **Use semantic colors** - `primary`, `success`, `warning`, etc.
2. **Leverage glassmorphism** - Use `.premium-card` or `.glass-card`
3. **Add glows for emphasis** - Icon backgrounds and buttons have auto glows
4. **Use proper transitions** - `.transition-smooth` for most interactions
5. **Icon containers** - Always wrap icons in `.icon-bg-*` containers
6. **Rounded corners** - Use `rounded-xl` for cards, `rounded-lg` for buttons
7. **Proper spacing** - Cards have `p-6` or `p-7`, dialogs have `gap-5`
8. **Focus states** - All interactive elements have glow on focus

---

## 🚀 Quick Reference

### Most Common Patterns

**Premium Card:**
```tsx
<Card className="premium-card p-6">Content</Card>
```

**Glass Dialog:**
```tsx
<DialogContent className="glass-strong">Content</DialogContent>
```

**Primary Button:**
```tsx
<Button className="bg-primary hover:bg-primary-hover">Action</Button>
```

**Icon with Background:**
```tsx
<div className="p-3 icon-bg-primary rounded-xl">
  <Icon className="icon-primary" />
</div>
```

**Status Badge:**
```tsx
<Badge className="badge-success">Status</Badge>
```

**Input Field:**
```tsx
<Input className="bg-input-background border-input" />
```

---

## 🎨 Color Variables

Direct access to CSS variables:
- `--primary`, `--primary-hover`, `--primary-light`, `--primary-glow`
- `--success`, `--success-hover`, `--success-light`, `--success-glow`
- `--warning`, `--warning-hover`, `--warning-light`, `--warning-glow`
- `--destructive`, `--destructive-hover`, `--destructive-light`, `--destructive-glow`
- `--info`, `--info-hover`, `--info-light`, `--info-glow`
- `--premium`, `--premium-hover`, `--premium-light`, `--premium-glow`

Use in inline styles:
```tsx
<div style={{ background: 'var(--primary-light)' }}>...</div>
```
