# AARO UI - Enterprise Revenue Operations Control Panel

A clean, professional web interface for the Autonomous AI Agent for Revenue Operations (AARO).

## 🎯 Design Principles

- **Enterprise-grade**: Professional B2B SaaS design
- **Control & Observability**: Focus on monitoring and control, not heavy dashboards
- **Trust & Transparency**: Clear explanations of AI decisions
- **Human Oversight**: Prominent approval workflows

## 🚀 Quick Start

### Option 1: Python Server (Recommended)
```bash
# Navigate to UI directory
cd ui

# Start the UI server
python server.py
```

### Option 2: Direct File Access
Simply open `index.html` in your browser.

### Prerequisites
- AARO API server running at `http://localhost:8000`
- Modern web browser (Chrome, Firefox, Safari, Edge)

## 📱 Features

### 1. Overview Dashboard
- **System Health**: Real-time status indicator
- **Key Metrics**: Deals monitored, active risks, actions executed, pending approvals
- **Visual Charts**: Risk distribution and action volume trends
- **Recent Activity**: Live feed of AI decisions and actions

### 2. Pipeline Risk Monitor
- **Risk Table**: Comprehensive view of flagged deals
- **Risk Details**: Click any deal for detailed analysis
- **Action Buttons**: Execute or request approval for recommendations
- **Filtering**: Sort by risk type, severity, rep, or stage

### 3. AI Decisions & Recommendations
- **Decision Cards**: Clear summaries of AI reasoning
- **Confidence Scores**: Transparency in AI decision-making
- **Action Status**: Track execution and approval status
- **Plain English**: Business-friendly explanations

### 4. Human-in-the-Loop Approvals
- **Approval Queue**: Pending requests requiring human oversight
- **Risk Assessment**: Clear impact and reasoning for each request
- **Action Buttons**: Approve, reject, or escalate decisions
- **Response Tracking**: Audit trail of human decisions

### 5. Action Execution Log
- **Chronological Log**: Complete history of AI actions
- **Filtering**: By action type, date, rep, or deal
- **Outcome Tracking**: Success/failure status for each action
- **Audit Trail**: Full transparency for compliance

### 6. Observability & Audit
- **System Metrics**: Performance and usage statistics
- **Audit Trail**: Searchable log of all system activities
- **Compliance**: Full transparency for regulatory requirements
- **Health Monitoring**: System status and uptime tracking

## 🎨 UI Components

### Navigation
- **Sidebar**: Clean, icon-based navigation
- **Active States**: Clear indication of current page
- **Badges**: Real-time counts for urgent items
- **System Status**: Always-visible health indicator

### Data Display
- **Metric Cards**: Key performance indicators
- **Data Tables**: Sortable, filterable deal information
- **Charts**: Visual representation of trends and distributions
- **Status Badges**: Color-coded severity and status indicators

### Interactions
- **Side Panels**: Detailed views without page navigation
- **Action Buttons**: Clear calls-to-action for each decision
- **Loading States**: Smooth user experience during data fetching
- **Error Handling**: Graceful degradation and error messages

## 🔧 Technical Details

### Architecture
- **Frontend**: Vanilla JavaScript (no framework dependencies)
- **Styling**: Custom CSS with CSS variables for theming
- **Charts**: Chart.js for data visualization
- **Icons**: Font Awesome for consistent iconography

### API Integration
- **Base URL**: Configurable API endpoint (default: localhost:8000)
- **Authentication**: Bearer token support
- **Error Handling**: Graceful API failure handling
- **Auto-refresh**: Configurable data refresh intervals

### Responsive Design
- **Mobile-friendly**: Responsive layout for tablets and phones
- **Sidebar**: Collapsible navigation on smaller screens
- **Tables**: Horizontal scrolling for data tables
- **Touch-friendly**: Appropriate button sizes for touch interfaces

## 🎯 Business Value

### For Sales Leaders
- **Pipeline Visibility**: Instant view of revenue risks
- **Performance Tracking**: Rep and team performance metrics
- **Decision Oversight**: Control over high-impact AI decisions

### For RevOps Teams
- **Automation Control**: Monitor and manage AI actions
- **Process Compliance**: Ensure SOP adherence across the team
- **Audit Trail**: Complete transparency for compliance and analysis

### For Executives
- **Revenue Protection**: Early warning system for pipeline risks
- **ROI Tracking**: Measure the impact of AI interventions
- **Operational Efficiency**: Reduce manual RevOps overhead

## 🔒 Security & Compliance

### Authentication
- **Token-based**: Secure API access with Bearer tokens
- **Session Management**: Automatic token refresh and logout
- **Role-based Access**: Different views for different user roles

### Audit Trail
- **Complete Logging**: Every action and decision logged
- **Searchable History**: Find any past action or decision
- **Compliance Ready**: Meets regulatory audit requirements

### Data Privacy
- **No Data Storage**: UI doesn't store sensitive business data
- **API-only**: All data fetched from secure API endpoints
- **HTTPS Ready**: Secure communication protocols

## 🚀 Deployment

### Development
```bash
python server.py
```

### Production
- Deploy static files to CDN or web server
- Configure API endpoint for production environment
- Set up HTTPS and security headers
- Enable caching for static assets

### Environment Configuration
```javascript
// In app.js, update the API base URL
this.apiBaseUrl = 'https://your-aaro-api.com';
```

## 📊 Metrics & Analytics

The UI tracks user interactions and system performance:
- Page views and navigation patterns
- Action execution rates
- Approval response times
- Error rates and user feedback

## 🔄 Auto-refresh

- **Default**: 5-minute refresh interval
- **Configurable**: Adjust refresh rate based on needs
- **Manual Refresh**: Always available via refresh button
- **Smart Updates**: Only refresh visible data

## 🎨 Customization

### Theming
The UI uses CSS variables for easy theming:
```css
:root {
    --primary-color: #2563eb;
    --success-color: #059669;
    --warning-color: #d97706;
    --danger-color: #dc2626;
}
```

### Branding
- Update logo and colors in `styles.css`
- Modify company name and branding text
- Customize metric cards and layouts

## 📱 Browser Support

- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+

## 🐛 Troubleshooting

### Common Issues

**UI not loading data:**
- Check AARO API is running at `http://localhost:8000`
- Verify API authentication token
- Check browser console for errors

**Charts not displaying:**
- Ensure Chart.js is loaded
- Check for JavaScript errors in console
- Verify data format matches chart expectations

**Responsive issues:**
- Clear browser cache
- Check viewport meta tag
- Verify CSS media queries

### Debug Mode
Enable debug logging by adding to browser console:
```javascript
window.aaroApp.debugMode = true;
```

## 🤝 Contributing

1. Follow the existing code style and patterns
2. Test on multiple browsers and screen sizes
3. Ensure accessibility compliance
4. Update documentation for new features

## 📄 License

Enterprise license - Contact for commercial use terms.