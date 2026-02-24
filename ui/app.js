// AARO UI Application JavaScript

class AAROApp {
    constructor() {
        // Auto-detect API URL based on environment
        this.apiBaseUrl = this.getApiBaseUrl();
        this.currentPage = 'overview';
        this.refreshInterval = null;
        this.init();
    }

    getApiBaseUrl() {
        // Check if we're in development (localhost:3000)
        if (window.location.hostname === 'localhost' && window.location.port === '3000') {
            return 'http://localhost:8000';
        }
        
        // For deployed version, use relative paths through nginx proxy
        if (window.location.hostname !== 'localhost') {
            return window.location.origin + '/api';
        }
        
        // Default fallback
        return 'http://localhost:8000';
    }

    init() {
        this.setupNavigation();
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoRefresh();
    }

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const page = item.dataset.page;
                this.navigateToPage(page);
            });
        });
    }

    setupEventListeners() {
        // Refresh button
        window.refreshData = () => {
            this.loadPageData(this.currentPage);
        };

        // Reset demo data button
        window.resetDemoData = () => {
            if (confirm('This will reset all demo data to the original state. Are you sure?')) {
                this.resetDemoData();
            }
        };

        // Side panel close
        window.closeSidePanel = () => {
            document.getElementById('side-panel').classList.remove('open');
        };

        // Deal row clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.deal-row')) {
                const dealId = e.target.closest('.deal-row').dataset.dealId;
                this.showDealDetails(dealId);
            }
        });

        // Tab switching
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('tab-btn')) {
                const tabName = e.target.dataset.tab;
                this.switchTab(e.target, tabName);
            }
        });

        // Confidence threshold slider
        document.addEventListener('input', (e) => {
            if (e.target.id === 'ai-confidence-threshold') {
                document.getElementById('confidence-value').textContent = e.target.value + '%';
            }
        });
    }

    navigateToPage(page) {
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-page="${page}"]`).classList.add('active');

        // Update page content
        document.querySelectorAll('.page').forEach(p => {
            p.classList.remove('active');
        });
        document.getElementById(`${page}-page`).classList.add('active');

        // Update header
        const pageTitle = page.split('-').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
        document.getElementById('page-title').textContent = pageTitle;
        document.getElementById('current-page').textContent = pageTitle;

        this.currentPage = page;
        this.loadPageData(page);
    }

    async loadInitialData() {
        // Initialize localStorage with default data if empty
        this.initializeDefaultData();
        
        await this.loadPageData('overview');
        this.updateLastRefreshed();
    }

    initializeDefaultData() {
        // Initialize approvals if not exists
        if (!localStorage.getItem('aaroApprovals')) {
            const defaultApprovals = [
                {
                    id: 'APP-001',
                    dealId: 'DEAL-002',
                    recommendation: 'Schedule urgent call with TechStart Inc decision maker',
                    impact: '$75,000 deal at risk',
                    riskLevel: 'High',
                    reasoning: 'Deal stalled for 21 days with no scheduled next action',
                    timestamp: '15 minutes ago'
                },
                {
                    id: 'APP-002',
                    dealId: 'DEAL-004',
                    recommendation: 'Offer 10% discount to close Enterprise Corp deal',
                    impact: '$200,000 potential revenue',
                    riskLevel: 'Medium',
                    reasoning: 'Competitor pricing pressure detected',
                    timestamp: '1 hour ago'
                }
            ];
            localStorage.setItem('aaroApprovals', JSON.stringify(defaultApprovals));
        }
    }

    // Reset all demo data to original state
    resetDemoData() {
        // Clear all existing data
        localStorage.removeItem('aaroDeals');
        localStorage.removeItem('aaroPlaybooks');
        localStorage.removeItem('aaroTeam');
        localStorage.removeItem('aaroRules');
        localStorage.removeItem('aaroApprovals');
        localStorage.removeItem('aaroPipelineRisks');
        localStorage.removeItem('aaroExecutedActions');
        localStorage.removeItem('aaroActionLog');
        localStorage.removeItem('aaroApprovedHistory');
        localStorage.removeItem('aaroRejectedHistory');

        // Reset to original demo data
        this.setOriginalDemoData();
        
        // Refresh current page
        this.loadPageData(this.currentPage);
        this.updateLastRefreshed();
        
        alert('Demo data has been reset to original state!');
    }

    setOriginalDemoData() {
        // Original deals
        const originalDeals = [
            {
                id: 'DEAL-001',
                company: 'Enterprise Corp',
                value: '$125,000',
                stage: 'Proposal',
                rep: 'Sarah Johnson',
                contact: 'John Smith',
                email: 'john@enterprise-corp.com',
                phone: '+1 (555) 123-4567',
                closeDate: '2026-02-28',
                notes: 'High-value enterprise deal with strong potential',
                created: '2026-01-15'
            },
            {
                id: 'DEAL-002',
                company: 'TechStart Inc',
                value: '$75,000',
                stage: 'Negotiation',
                rep: 'Mike Chen',
                contact: 'Jane Doe',
                email: 'jane@techstart.com',
                phone: '+1 (555) 987-6543',
                closeDate: '2026-02-15',
                notes: 'Mid-market opportunity with competitive pressure',
                created: '2026-01-20'
            },
            {
                id: 'DEAL-003',
                company: 'Growth Solutions',
                value: '$45,000',
                stage: 'Discovery',
                rep: 'Emily Davis',
                contact: 'Bob Wilson',
                email: 'bob@growthsolutions.com',
                phone: '+1 (555) 456-7890',
                closeDate: '2026-03-15',
                notes: 'SMB deal with good qualification potential',
                created: '2026-01-25'
            }
        ];
        localStorage.setItem('aaroDeals', JSON.stringify(originalDeals));

        // Original playbooks
        const originalPlaybooks = [
            {
                id: 'PB-001',
                title: 'Discovery Call Playbook',
                category: 'Discovery',
                content: 'Complete guide for conducting effective discovery calls with prospects. Includes qualification questions, pain point identification, and next step planning.',
                tags: ['discovery', 'qualification', 'calls'],
                created: '2026-01-10'
            },
            {
                id: 'PB-002',
                title: 'Enterprise Demo Script',
                category: 'Demo',
                content: 'Structured demo flow for enterprise prospects. Covers feature highlights, ROI calculations, and objection handling during product demonstrations.',
                tags: ['demo', 'enterprise', 'presentation'],
                created: '2026-01-12'
            },
            {
                id: 'PB-003',
                title: 'Objection Handling Guide',
                category: 'Objection Handling',
                content: 'Common objections and proven responses. Includes pricing objections, feature gaps, and competitive comparisons.',
                tags: ['objections', 'responses', 'competitive'],
                created: '2026-01-18'
            }
        ];
        localStorage.setItem('aaroPlaybooks', JSON.stringify(originalPlaybooks));

        // Original team
        const originalTeam = [
            {
                id: 'REP-001',
                name: 'Sarah Johnson',
                email: 'sarah@company.com',
                role: 'Senior AE',
                territory: 'Enterprise',
                quota: '$500,000',
                manager: 'Jane Doe',
                created: '2026-01-01'
            },
            {
                id: 'REP-002',
                name: 'Mike Chen',
                email: 'mike@company.com',
                role: 'Account Executive',
                territory: 'Mid-Market',
                quota: '$300,000',
                manager: 'Jane Doe',
                created: '2026-01-01'
            },
            {
                id: 'REP-003',
                name: 'Emily Davis',
                email: 'emily@company.com',
                role: 'Account Executive',
                territory: 'SMB',
                quota: '$200,000',
                manager: 'Bob Smith',
                created: '2026-01-01'
            }
        ];
        localStorage.setItem('aaroTeam', JSON.stringify(originalTeam));

        // Original AI rules
        const originalRules = [
            {
                id: 'RULE-001',
                name: 'Stalled Deal Detection',
                category: 'Risk Detection',
                trigger: 'No activity for 7 days',
                threshold: '7',
                action: 'Create follow-up task',
                description: 'Automatically detect deals that have been inactive for more than 7 days and create follow-up tasks.',
                active: true,
                created: '2026-01-05'
            },
            {
                id: 'RULE-002',
                name: 'High Value Deal Alert',
                category: 'Opportunity',
                trigger: 'Deal value > $100K',
                threshold: '100000',
                action: 'Send manager alert',
                description: 'Alert sales managers when high-value deals are created or updated.',
                active: true,
                created: '2026-01-05'
            },
            {
                id: 'RULE-003',
                name: 'SOP Compliance Check',
                category: 'Compliance',
                trigger: 'SOP step missed',
                threshold: '1',
                action: 'Send reminder',
                description: 'Monitor sales process compliance and send reminders for missed steps.',
                active: true,
                created: '2026-01-05'
            }
        ];
        localStorage.setItem('aaroRules', JSON.stringify(originalRules));

        // Original approvals
        const originalApprovals = [
            {
                id: 'APP-001',
                dealId: 'DEAL-002',
                recommendation: 'Schedule urgent call with TechStart Inc decision maker',
                impact: '$75,000 deal at risk',
                riskLevel: 'High',
                reasoning: 'Deal stalled for 21 days with no scheduled next action',
                timestamp: '15 minutes ago'
            },
            {
                id: 'APP-002',
                dealId: 'DEAL-004',
                recommendation: 'Offer 10% discount to close Enterprise Corp deal',
                impact: '$200,000 potential revenue',
                riskLevel: 'Medium',
                reasoning: 'Competitor pricing pressure detected',
                timestamp: '1 hour ago'
            }
        ];
        localStorage.setItem('aaroApprovals', JSON.stringify(originalApprovals));

        // Original pipeline risks
        const originalRisks = [
            {
                dealId: 'DEAL-001',
                rep: 'Sarah Johnson',
                stage: 'Proposal',
                riskType: 'Stalled Deal',
                severity: 'High',
                value: '$125,000',
                recommendedAction: 'Schedule urgent follow-up call',
                daysStalled: 14,
                totalActions: 3
            },
            {
                dealId: 'DEAL-002',
                rep: 'Mike Chen',
                stage: 'Negotiation',
                riskType: 'No Recent Activity',
                severity: 'Medium',
                value: '$75,000',
                recommendedAction: 'Send check-in email',
                daysStalled: 7,
                totalActions: 2
            },
            {
                dealId: 'DEAL-003',
                rep: 'Emily Davis',
                stage: 'Discovery',
                riskType: 'SOP Deviation',
                severity: 'Low',
                value: '$45,000',
                recommendedAction: 'Complete qualification checklist',
                daysStalled: 3,
                totalActions: 1
            }
        ];
        localStorage.setItem('aaroPipelineRisks', JSON.stringify(originalRisks));

        // Original action log with real timestamps
        const now = new Date();
        const originalActionLog = [
            {
                id: 'ACT-001',
                type: 'Task Creation',
                description: 'Created follow-up task for DEAL-001',
                outcome: 'Task assigned to Sarah Johnson',
                timestamp: new Date(now.getTime() - 2 * 60 * 1000).toISOString(),
                status: 'Success'
            },
            {
                id: 'ACT-002',
                type: 'CRM Update',
                description: 'Updated deal stage for DEAL-003',
                outcome: 'Stage changed to Negotiation',
                timestamp: new Date(now.getTime() - 15 * 60 * 1000).toISOString(),
                status: 'Success'
            },
            {
                id: 'ACT-003',
                type: 'Alert Sent',
                description: 'Manager alert for high-risk deal',
                outcome: 'Email sent to sales manager',
                timestamp: new Date(now.getTime() - 60 * 60 * 1000).toISOString(),
                status: 'Success'
            },
            {
                id: 'ACT-004',
                type: 'Email Sequence',
                description: 'Started nurturing sequence for 5 leads',
                outcome: 'Sequence initiated successfully',
                timestamp: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
                status: 'Success'
            }
        ];
        localStorage.setItem('aaroActionLog', JSON.stringify(originalActionLog));
    }

    async loadPageData(page) {
        this.showLoading();
        
        try {
            switch (page) {
                case 'overview':
                    await this.loadOverviewData();
                    break;
                case 'pipeline-risks':
                    await this.loadPipelineRisks();
                    break;
                case 'ai-decisions':
                    await this.loadAIDecisions();
                    break;
                case 'approvals':
                    await this.loadApprovals();
                    break;
                case 'action-log':
                    await this.loadActionLog();
                    break;
                case 'observability':
                    await this.loadObservabilityData();
                    break;
                case 'data-management':
                    await this.loadDataManagement();
                    break;
                case 'configuration':
                    await this.loadConfiguration();
                    break;
                default:
                    console.warn(`Unknown page: ${page}`);
            }
            
            // Update last refreshed time
            this.updateLastRefreshed();
            
        } catch (error) {
            console.error('Error loading page data:', error);
            
            // Show user-friendly error message
            const errorMessage = error.message || 'Unknown error occurred';
            console.log('Detailed error for debugging:', error);
            
            // Don't show alert for overview page errors, just log them
            if (page !== 'overview') {
                this.showError(`Failed to load ${page} data: ${errorMessage}`);
            }
        } finally {
            this.hideLoading();
        }
    }

    async loadOverviewData() {
        try {
            // Load overview metrics and charts
            this.updateOverviewMetrics();
            this.initializeCharts();
        } catch (error) {
            console.error('Error loading overview data:', error);
            // Don't throw the error, just log it and continue
        }
    }

    updateOverviewMetrics() {
        // Update metrics based on current data
        const deals = JSON.parse(localStorage.getItem('aaroDeals') || '[]');
        const approvals = JSON.parse(localStorage.getItem('aaroApprovals') || '[]');
        const rules = JSON.parse(localStorage.getItem('aaroRules') || '[]');
        
        // Update deals monitored
        const dealsElement = document.querySelector('.metric-card:nth-child(1) .metric-value');
        if (dealsElement) {
            dealsElement.textContent = deals.length || '247';
        }
        
        // Update pending approvals
        const approvalsElement = document.querySelector('.metric-card:nth-child(4) .metric-value');
        if (approvalsElement) {
            approvalsElement.textContent = approvals.length;
        }
        
        // Update active rules (could represent risks)
        const activeRules = rules.filter(rule => rule.active).length;
        const risksElement = document.querySelector('.metric-card:nth-child(2) .metric-value');
        if (risksElement) {
            risksElement.textContent = activeRules || '8';
        }
    }

    async loadPipelineRisks() {
        // Get base risks from localStorage or use mock data
        let mockRisks = JSON.parse(localStorage.getItem('aaroPipelineRisks') || 'null');
        
        if (!mockRisks) {
            mockRisks = [
                {
                    dealId: 'DEAL-001',
                    rep: 'Sarah Johnson',
                    stage: 'Proposal',
                    riskType: 'Stalled Deal',
                    severity: 'High',
                    value: '$125,000',
                    recommendedAction: 'Schedule urgent follow-up call',
                    daysStalled: 14,
                    totalActions: 3 // Total number of recommended actions for this deal
                },
                {
                    dealId: 'DEAL-002',
                    rep: 'Mike Chen',
                    stage: 'Negotiation',
                    riskType: 'No Recent Activity',
                    severity: 'Medium',
                    value: '$75,000',
                    recommendedAction: 'Send check-in email',
                    daysStalled: 7,
                    totalActions: 2
                },
                {
                    dealId: 'DEAL-003',
                    rep: 'Emily Davis',
                    stage: 'Discovery',
                    riskType: 'SOP Deviation',
                    severity: 'Low',
                    value: '$45,000',
                    recommendedAction: 'Complete qualification checklist',
                    daysStalled: 3,
                    totalActions: 1
                }
            ];
            localStorage.setItem('aaroPipelineRisks', JSON.stringify(mockRisks));
        }

        // Get executed actions to check which risks are resolved
        const executedActions = JSON.parse(localStorage.getItem('aaroExecutedActions') || '{}');
        
        // Filter out resolved risks (where all actions have been executed)
        const activeRisks = mockRisks.filter(risk => {
            const dealExecutedActions = executedActions[risk.dealId] || [];
            const executedCount = dealExecutedActions.length;
            
            // Risk is resolved if all actions have been executed
            return executedCount < risk.totalActions;
        });

        const tbody = document.getElementById('risks-table-body');
        
        if (activeRisks.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state-row">
                        <div class="empty-state">
                            <i class="fas fa-check-circle"></i>
                            <h3>No Active Pipeline Risks</h3>
                            <p>Great work! All identified risks have been addressed.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = activeRisks.map(risk => {
            const dealExecutedActions = executedActions[risk.dealId] || [];
            const executedCount = dealExecutedActions.length;
            const progressText = executedCount > 0 ? ` (${executedCount}/${risk.totalActions} actions completed)` : '';
            
            return `
                <tr class="deal-row ${executedCount > 0 ? 'in-progress' : ''}" data-deal-id="${risk.dealId}">
                    <td><strong>${risk.dealId}</strong></td>
                    <td>${risk.rep}</td>
                    <td>${risk.stage}</td>
                    <td>${risk.riskType}${progressText}</td>
                    <td><span class="status-badge ${risk.severity.toLowerCase()}">${risk.severity}</span></td>
                    <td><strong>${risk.value}</strong></td>
                    <td>${risk.recommendedAction}</td>
                    <td>
                        <button class="btn primary" onclick="executeAction('${risk.dealId}')">Execute</button>
                        <button class="btn secondary" onclick="requestApproval('${risk.dealId}')">Approve</button>
                        ${executedCount > 0 ? `<div class="progress-indicator">${executedCount}/${risk.totalActions} done</div>` : ''}
                    </td>
                </tr>
            `;
        }).join('');
    }

    async loadAIDecisions() {
        const mockDecisions = [
            {
                id: 'DEC-001',
                type: 'Risk Detection',
                summary: 'High-value deal flagged for immediate attention',
                action: 'Create follow-up task and alert manager',
                status: 'Executed',
                timestamp: '2 minutes ago',
                confidence: 95
            },
            {
                id: 'DEC-002',
                type: 'Process Optimization',
                summary: 'Lead nurturing sequence recommended',
                action: 'Initiate automated email sequence',
                status: 'Pending Approval',
                timestamp: '15 minutes ago',
                confidence: 87
            },
            {
                id: 'DEC-003',
                type: 'Compliance Check',
                summary: 'SOP deviation detected in qualification process',
                action: 'Send reminder to complete required steps',
                status: 'Executed',
                timestamp: '1 hour ago',
                confidence: 92
            }
        ];

        const container = document.getElementById('decisions-grid');
        container.innerHTML = mockDecisions.map(decision => `
            <div class="decision-card">
                <div class="decision-header">
                    <div class="decision-type">${decision.type}</div>
                    <div class="decision-status ${decision.status.toLowerCase().replace(' ', '-')}">${decision.status}</div>
                </div>
                <div class="decision-content">
                    <h4>${decision.summary}</h4>
                    <p><strong>Action:</strong> ${decision.action}</p>
                    <div class="decision-meta">
                        <span>Confidence: ${decision.confidence}%</span>
                        <span>${decision.timestamp}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async loadApprovals() {
        // Get approvals from localStorage or use mock data
        let mockApprovals = JSON.parse(localStorage.getItem('aaroApprovals') || 'null') || [
            {
                id: 'APP-001',
                dealId: 'DEAL-002',
                recommendation: 'Schedule urgent call with TechStart Inc decision maker',
                impact: '$75,000 deal at risk',
                riskLevel: 'High',
                reasoning: 'Deal stalled for 21 days with no scheduled next action',
                timestamp: '15 minutes ago'
            },
            {
                id: 'APP-002',
                dealId: 'DEAL-004',
                recommendation: 'Offer 10% discount to close Enterprise Corp deal',
                impact: '$200,000 potential revenue',
                riskLevel: 'Medium',
                reasoning: 'Competitor pricing pressure detected',
                timestamp: '1 hour ago'
            }
        ];

        const container = document.getElementById('approvals-queue');
        
        if (mockApprovals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-check-circle"></i>
                    <h3>All caught up!</h3>
                    <p>No pending approvals at this time. Great work!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = mockApprovals.map(approval => `
            <div class="approval-card">
                <div class="approval-header">
                    <div class="approval-id">${approval.id}</div>
                    <div class="risk-level ${approval.riskLevel.toLowerCase()}">${approval.riskLevel} Risk</div>
                    ${approval.status === 'escalated' ? '<div class="escalated-badge">Escalated</div>' : ''}
                </div>
                <div class="approval-content">
                    <h4>${approval.recommendation}</h4>
                    <div class="approval-details">
                        <div class="detail-row">
                            <strong>Expected Impact:</strong> ${approval.impact}
                        </div>
                        <div class="detail-row">
                            <strong>Reasoning:</strong> ${approval.reasoning}
                        </div>
                        <div class="detail-row">
                            <strong>Submitted:</strong> ${approval.timestamp}
                        </div>
                        ${approval.escalatedAt ? `
                            <div class="detail-row">
                                <strong>Escalated:</strong> ${new Date(approval.escalatedAt).toLocaleString()}
                            </div>
                        ` : ''}
                    </div>
                    <div class="approval-actions">
                        ${approval.status !== 'escalated' ? `
                            <button class="btn success" onclick="approveRequest('${approval.id}')">
                                <i class="fas fa-check"></i> Approve
                            </button>
                            <button class="btn danger" onclick="rejectRequest('${approval.id}')">
                                <i class="fas fa-times"></i> Reject
                            </button>
                            <button class="btn secondary" onclick="escalateRequest('${approval.id}')">
                                <i class="fas fa-arrow-up"></i> Escalate
                            </button>
                        ` : `
                            <div class="escalated-message">
                                <i class="fas fa-clock"></i> Waiting for senior management review
                            </div>
                        `}
                    </div>
                </div>
            </div>
        `).join('');
    }

    async loadActionLog() {
        // Get actions from localStorage or initialize with timestamped mock data
        let mockActions = JSON.parse(localStorage.getItem('aaroActionLog') || 'null');
        
        if (!mockActions) {
            // Initialize with real timestamps
            const now = new Date();
            mockActions = [
                {
                    id: 'ACT-001',
                    type: 'Task Creation',
                    description: 'Created follow-up task for DEAL-001',
                    outcome: 'Task assigned to Sarah Johnson',
                    timestamp: new Date(now.getTime() - 2 * 60 * 1000).toISOString(), // 2 minutes ago
                    status: 'Success'
                },
                {
                    id: 'ACT-002',
                    type: 'CRM Update',
                    description: 'Updated deal stage for DEAL-003',
                    outcome: 'Stage changed to Negotiation',
                    timestamp: new Date(now.getTime() - 15 * 60 * 1000).toISOString(), // 15 minutes ago
                    status: 'Success'
                },
                {
                    id: 'ACT-003',
                    type: 'Alert Sent',
                    description: 'Manager alert for high-risk deal',
                    outcome: 'Email sent to sales manager',
                    timestamp: new Date(now.getTime() - 60 * 60 * 1000).toISOString(), // 1 hour ago
                    status: 'Success'
                },
                {
                    id: 'ACT-004',
                    type: 'Email Sequence',
                    description: 'Started nurturing sequence for 5 leads',
                    outcome: 'Sequence initiated successfully',
                    timestamp: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
                    status: 'Success'
                }
            ];
            
            // Save to localStorage
            localStorage.setItem('aaroActionLog', JSON.stringify(mockActions));
        }

        const container = document.getElementById('action-log-container');
        container.innerHTML = mockActions.map(action => `
            <div class="log-entry">
                <div class="log-header">
                    <div class="log-type">${action.type}</div>
                    <div class="log-status ${action.status.toLowerCase()}">${action.status}</div>
                    <div class="log-timestamp">${this.getRelativeTime(action.timestamp)}</div>
                </div>
                <div class="log-content">
                    <div class="log-description">${action.description}</div>
                    <div class="log-outcome">${action.outcome}</div>
                </div>
            </div>
        `).join('');
    }

    // Utility function to calculate relative time
    getRelativeTime(timestamp) {
        const now = new Date();
        const actionTime = new Date(timestamp);
        const diffInSeconds = Math.floor((now - actionTime) / 1000);
        
        if (diffInSeconds < 60) {
            return `${diffInSeconds} seconds ago`;
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
        } else if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
        } else {
            const days = Math.floor(diffInSeconds / 86400);
            return `${days} day${days !== 1 ? 's' : ''} ago`;
        }
    }

    async loadObservabilityData() {
        const mockAuditLog = [
            {
                timestamp: '2026-01-30 16:05:23',
                user: 'AARO System',
                action: 'Risk Detection',
                details: 'Flagged DEAL-001 for stalled activity'
            },
            {
                timestamp: '2026-01-30 16:03:15',
                user: 'Sarah Johnson',
                action: 'Approval Response',
                details: 'Approved follow-up action for DEAL-002'
            },
            {
                timestamp: '2026-01-30 16:01:45',
                user: 'AARO System',
                action: 'Action Execution',
                details: 'Created 3 follow-up tasks automatically'
            }
        ];

        const container = document.getElementById('audit-log');
        container.innerHTML = mockAuditLog.map(entry => `
            <div class="audit-entry">
                <div class="audit-timestamp">${entry.timestamp}</div>
                <div class="audit-user">${entry.user}</div>
                <div class="audit-action">${entry.action}</div>
                <div class="audit-details">${entry.details}</div>
            </div>
        `).join('');
    }

    async loadDataManagement() {
        this.setupDataManagementTabs();
        this.loadDealsData();
        this.loadPlaybooksData();
        this.loadTeamData();
    }

    async loadConfiguration() {
        this.setupConfigurationTabs();
        this.loadAIRulesData();
    }

    setupDataManagementTabs() {
        const tabs = document.querySelectorAll('.data-management-tabs .tab-btn');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchDataTab(tab, tab.dataset.tab);
            });
        });
    }

    setupConfigurationTabs() {
        const tabs = document.querySelectorAll('.config-tabs .tab-btn');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchConfigTab(tab, tab.dataset.tab);
            });
        });
    }

    switchTab(clickedTab, tabName) {
        // Remove active class from all tabs and content
        clickedTab.parentElement.querySelectorAll('.tab-btn').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Add active class to clicked tab
        clickedTab.classList.add('active');
        
        // Switch content
        const contentContainer = clickedTab.closest('.page');
        contentContainer.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const targetContent = contentContainer.querySelector(`#${tabName}-tab`);
        if (targetContent) {
            targetContent.classList.add('active');
        }
    }

    switchDataTab(clickedTab, tabName) {
        this.switchTab(clickedTab, tabName);
    }

    switchConfigTab(clickedTab, tabName) {
        this.switchTab(clickedTab, tabName);
    }

    loadDealsData() {
        // Get deals from storage or use mock data
        let mockDeals = JSON.parse(localStorage.getItem('aaroDeals') || 'null') || [
            {
                id: 'DEAL-001',
                company: 'Enterprise Corp',
                value: '$125,000',
                stage: 'Proposal',
                rep: 'Sarah Johnson',
                contact: 'John Smith',
                created: '2026-01-15'
            },
            {
                id: 'DEAL-002',
                company: 'TechStart Inc',
                value: '$75,000',
                stage: 'Negotiation',
                rep: 'Mike Chen',
                contact: 'Jane Doe',
                created: '2026-01-20'
            }
        ];

        const container = document.getElementById('deals-list');
        if (mockDeals.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-handshake"></i><h3>No deals found</h3><p>Add your first deal to get started</p></div>';
            return;
        }

        container.innerHTML = mockDeals.map(deal => `
            <div class="deal-item">
                <div class="deal-header">
                    <h5>${deal.company}</h5>
                    <span class="deal-value">${deal.value}</span>
                </div>
                <div class="deal-details">
                    <span>Stage: ${deal.stage}</span>
                    <span>Rep: ${deal.rep}</span>
                    <span>Contact: ${deal.contact}</span>
                </div>
                <div class="deal-actions">
                    <button class="btn secondary btn-sm" onclick="editDeal('${deal.id}')">Edit</button>
                    <button class="btn danger btn-sm" onclick="deleteDeal('${deal.id}')">Delete</button>
                </div>
            </div>
        `).join('');
    }

    loadPlaybooksData() {
        let mockPlaybooks = JSON.parse(localStorage.getItem('aaroPlaybooks') || 'null') || [
            {
                id: 'PB-001',
                title: 'Discovery Call Playbook',
                category: 'Discovery',
                tags: ['discovery', 'qualification'],
                created: '2026-01-10'
            },
            {
                id: 'PB-002',
                title: 'Enterprise Demo Script',
                category: 'Demo',
                tags: ['demo', 'enterprise', 'presentation'],
                created: '2026-01-12'
            }
        ];

        const container = document.getElementById('playbooks-list');
        if (mockPlaybooks.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-book"></i><h3>No playbooks found</h3><p>Add your first sales playbook to get started</p></div>';
            return;
        }

        container.innerHTML = mockPlaybooks.map(playbook => `
            <div class="playbook-item">
                <div class="playbook-header">
                    <h5>${playbook.title}</h5>
                    <span class="playbook-category">${playbook.category}</span>
                </div>
                <div class="playbook-tags">
                    ${playbook.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
                <div class="playbook-actions">
                    <button class="btn secondary btn-sm" onclick="editPlaybook('${playbook.id}')">Edit</button>
                    <button class="btn danger btn-sm" onclick="deletePlaybook('${playbook.id}')">Delete</button>
                </div>
            </div>
        `).join('');
    }

    loadTeamData() {
        let mockTeam = JSON.parse(localStorage.getItem('aaroTeam') || 'null') || [
            {
                id: 'REP-001',
                name: 'Sarah Johnson',
                email: 'sarah@company.com',
                role: 'Senior AE',
                territory: 'Enterprise',
                quota: '$50,000'
            },
            {
                id: 'REP-002',
                name: 'Mike Chen',
                email: 'mike@company.com',
                role: 'Account Executive',
                territory: 'SMB',
                quota: '$30,000'
            }
        ];

        const container = document.getElementById('team-list');
        if (mockTeam.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><h3>No team members found</h3><p>Add your first sales rep to get started</p></div>';
            return;
        }

        container.innerHTML = mockTeam.map(rep => `
            <div class="team-item">
                <div class="team-header">
                    <h5>${rep.name}</h5>
                    <span class="team-role">${rep.role}</span>
                </div>
                <div class="team-details">
                    <span>Email: ${rep.email}</span>
                    <span>Territory: ${rep.territory}</span>
                    <span>Quota: ${rep.quota}</span>
                </div>
                <div class="team-actions">
                    <button class="btn secondary btn-sm" onclick="editRep('${rep.id}')">Edit</button>
                    <button class="btn danger btn-sm" onclick="deleteRep('${rep.id}')">Delete</button>
                </div>
            </div>
        `).join('');
    }

    loadAIRulesData() {
        let mockRules = JSON.parse(localStorage.getItem('aaroRules') || 'null') || [
            {
                id: 'RULE-001',
                name: 'Stalled Deal Detection',
                category: 'Risk Detection',
                trigger: 'No activity for 7 days',
                action: 'Create follow-up task',
                active: true
            },
            {
                id: 'RULE-002',
                name: 'High Value Deal Alert',
                category: 'Opportunity',
                trigger: 'Deal value > $100K',
                action: 'Send manager alert',
                active: true
            }
        ];

        const container = document.getElementById('rules-list');
        if (mockRules.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-cogs"></i><h3>No AI rules found</h3><p>Add your first AI decision rule to get started</p></div>';
            return;
        }

        container.innerHTML = mockRules.map(rule => `
            <div class="rule-item">
                <div class="rule-header">
                    <h5>${rule.name}</h5>
                    <div class="rule-status">
                        <label class="toggle-switch">
                            <input type="checkbox" ${rule.active ? 'checked' : ''} onchange="toggleRule('${rule.id}')">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
                <div class="rule-details">
                    <span>Category: ${rule.category}</span>
                    <span>Trigger: ${rule.trigger}</span>
                    <span>Action: ${rule.action}</span>
                </div>
                <div class="rule-actions">
                    <button class="btn secondary btn-sm" onclick="editRule('${rule.id}')">Edit</button>
                    <button class="btn danger btn-sm" onclick="deleteRule('${rule.id}')">Delete</button>
                </div>
            </div>
        `).join('');
    }

    initializeCharts() {
        // Risk Distribution Chart
        const riskCtx = document.getElementById('risk-chart');
        if (riskCtx) {
            new Chart(riskCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Stalled Deals', 'No Activity', 'SOP Deviations', 'Low Engagement'],
                    datasets: [{
                        data: [8, 5, 3, 2],
                        backgroundColor: ['#dc2626', '#d97706', '#059669', '#0891b2'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }

        // Action Volume Chart
        const actionCtx = document.getElementById('action-chart');
        if (actionCtx) {
            new Chart(actionCtx, {
                type: 'line',
                data: {
                    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    datasets: [{
                        label: 'Actions Executed',
                        data: [45, 52, 48, 61],
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    }

    showDealDetails(dealId) {
        const mockDealDetails = {
            'DEAL-001': {
                id: 'DEAL-001',
                company: 'Enterprise Corp',
                value: '$125,000',
                stage: 'Proposal',
                rep: 'Sarah Johnson',
                lastActivity: '14 days ago',
                riskFactors: [
                    'No activity for 14 days',
                    'Proposal sent but no response',
                    'Decision maker not engaged'
                ],
                sopViolations: [
                    'Missing follow-up within 7 days of proposal'
                ],
                confidence: 95,
                recommendedActions: [
                    'Schedule urgent call with decision maker',
                    'Send personalized follow-up email',
                    'Engage champion for internal advocacy'
                ]
            }
        };

        const deal = mockDealDetails[dealId];
        if (!deal) return;

        // Get executed actions from localStorage
        const executedActions = JSON.parse(localStorage.getItem('aaroExecutedActions') || '{}');
        const dealExecutedActions = executedActions[dealId] || [];

        const content = `
            <div class="deal-details">
                <div class="detail-section">
                    <h4>Deal Information</h4>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>Company:</label>
                            <span>${deal.company}</span>
                        </div>
                        <div class="detail-item">
                            <label>Value:</label>
                            <span><strong>${deal.value}</strong></span>
                        </div>
                        <div class="detail-item">
                            <label>Stage:</label>
                            <span>${deal.stage}</span>
                        </div>
                        <div class="detail-item">
                            <label>Rep:</label>
                            <span>${deal.rep}</span>
                        </div>
                        <div class="detail-item">
                            <label>Last Activity:</label>
                            <span>${deal.lastActivity}</span>
                        </div>
                    </div>
                </div>

                <div class="detail-section">
                    <h4>Risk Analysis</h4>
                    <div class="confidence-score">
                        <label>Confidence Score:</label>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${deal.confidence}%"></div>
                        </div>
                        <span>${deal.confidence}%</span>
                    </div>
                    <div class="risk-factors">
                        <h5>Risk Factors:</h5>
                        <ul>
                            ${deal.riskFactors.map(factor => `<li>${factor}</li>`).join('')}
                        </ul>
                    </div>
                    ${deal.sopViolations.length > 0 ? `
                        <div class="sop-violations">
                            <h5>SOP Violations:</h5>
                            <ul>
                                ${deal.sopViolations.map(violation => `<li>${violation}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>

                <div class="detail-section">
                    <h4>Recommended Actions</h4>
                    <div class="recommended-actions">
                        ${deal.recommendedActions.map((action, index) => {
                            const isExecuted = dealExecutedActions.some(exec => exec.actionIndex === index);
                            const executedInfo = dealExecutedActions.find(exec => exec.actionIndex === index);
                            
                            return `
                                <div class="action-item ${isExecuted ? 'executed' : ''}">
                                    <span class="action-priority">${index + 1}</span>
                                    <span class="action-text">${action}</span>
                                    ${isExecuted ? `
                                        <div class="executed-status">
                                            <i class="fas fa-check-circle"></i>
                                            <span>Executed</span>
                                            <div class="executed-time">${new Date(executedInfo.executedAt).toLocaleString()}</div>
                                        </div>
                                    ` : `
                                        <button class="btn primary btn-sm" onclick="executeAction('${deal.id}', ${index})">
                                            Execute
                                        </button>
                                    `}
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            </div>
        `;

        document.getElementById('side-panel-title').textContent = `Deal Details - ${dealId}`;
        document.getElementById('side-panel-content').innerHTML = content;
        document.getElementById('side-panel').classList.add('open');
    }

    showLoading() {
        document.getElementById('loading-overlay').classList.add('show');
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.remove('show');
    }

    showError(message) {
        // Simple error handling - could be enhanced with toast notifications
        alert(message);
    }

    updateLastRefreshed() {
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        document.getElementById('last-updated').textContent = `${timeString}`;
        
        // Update sidebar badges
        this.updateSidebarBadges();
    }

    updateSidebarBadges() {
        // Update approvals badge
        const approvals = JSON.parse(localStorage.getItem('aaroApprovals') || '[]');
        const approvalsBadge = document.querySelector('[data-page="approvals"] .badge');
        if (approvalsBadge) {
            if (approvals.length > 0) {
                approvalsBadge.textContent = approvals.length;
                approvalsBadge.classList.add('urgent');
                approvalsBadge.style.display = 'inline';
            } else {
                approvalsBadge.style.display = 'none';
            }
        }
        
        // Update pipeline risks badge (based on active risks)
        const allRisks = JSON.parse(localStorage.getItem('aaroPipelineRisks') || '[]');
        const executedActions = JSON.parse(localStorage.getItem('aaroExecutedActions') || '{}');
        
        // Count active risks (not fully resolved)
        const activeRisksCount = allRisks.filter(risk => {
            const dealExecutedActions = executedActions[risk.dealId] || [];
            const executedCount = dealExecutedActions.length;
            return executedCount < (risk.totalActions || 1);
        }).length;
        
        const risksBadge = document.querySelector('[data-page="pipeline-risks"] .badge');
        if (risksBadge) {
            if (activeRisksCount > 0) {
                risksBadge.textContent = activeRisksCount;
                risksBadge.style.display = 'inline';
            } else {
                risksBadge.style.display = 'none';
            }
        }
    }

    startAutoRefresh() {
        // Refresh data every 2 minutes
        this.refreshInterval = setInterval(() => {
            this.loadPageData(this.currentPage);
            this.updateLastRefreshed();
        }, 120000); // 2 minutes = 120,000 milliseconds
        
        // Update timestamps every 30 seconds for action log
        this.timestampInterval = setInterval(() => {
            if (this.currentPage === 'action-log') {
                this.loadActionLog();
            }
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.timestampInterval) {
            clearInterval(this.timestampInterval);
        }
    }
}

// Global action functions
window.executeAction = (dealId, actionIndex) => {
    console.log(`Executing action for deal ${dealId}, action ${actionIndex}`);
    
    try {
        // Get executed actions from localStorage
        let executedActions = JSON.parse(localStorage.getItem('aaroExecutedActions') || '{}');
        
        // Initialize deal's executed actions if not exists
        if (!executedActions[dealId]) {
            executedActions[dealId] = [];
        }
        
        // Add this action to executed list
        const executionTime = new Date().toISOString();
        executedActions[dealId].push({
            actionIndex: actionIndex,
            executedAt: executionTime,
            executedBy: 'Current User'
        });
        
        // Save back to localStorage
        localStorage.setItem('aaroExecutedActions', JSON.stringify(executedActions));
        
        // Add to action log
        let actionLog = JSON.parse(localStorage.getItem('aaroActionLog') || '[]');
        const newLogEntry = {
            id: 'ACT-' + Date.now(),
            type: 'Action Execution',
            description: `Executed recommended action for ${dealId}`,
            outcome: `Action ${actionIndex + 1} completed successfully`,
            timestamp: executionTime,
            status: 'Success'
        };
        
        // Add to beginning of array (most recent first)
        actionLog.unshift(newLogEntry);
        
        // Keep only last 50 entries
        if (actionLog.length > 50) {
            actionLog = actionLog.slice(0, 50);
        }
        
        localStorage.setItem('aaroActionLog', JSON.stringify(actionLog));
        
        alert(`Action executed successfully for deal ${dealId}!`);
        
        // Refresh the side panel to show updated status
        window.aaroApp.showDealDetails(dealId);
        
        // Also refresh the pipeline risks page if we're on it
        if (window.aaroApp.currentPage === 'pipeline-risks') {
            window.aaroApp.loadPipelineRisks();
        }
        
        // Refresh action log if we're on that page
        if (window.aaroApp.currentPage === 'action-log') {
            window.aaroApp.loadActionLog();
        }
        
    } catch (error) {
        console.error('Error executing action:', error);
        alert('Error executing action. Please try again.');
    }
};

window.requestApproval = (dealId) => {
    console.log(`Requesting approval for deal ${dealId}`);
    // Implement API call to request approval
    alert(`Approval requested for deal ${dealId}`);
};

window.approveRequest = (approvalId) => {
    console.log(`Approving request ${approvalId}`);
    
    try {
        // Get current approvals from localStorage or use mock data
        let approvals = JSON.parse(localStorage.getItem('aaroApprovals') || 'null') || [
            {
                id: 'APP-001',
                dealId: 'DEAL-002',
                recommendation: 'Schedule urgent call with TechStart Inc decision maker',
                impact: '$75,000 deal at risk',
                riskLevel: 'High',
                reasoning: 'Deal stalled for 21 days with no scheduled next action',
                timestamp: '15 minutes ago'
            },
            {
                id: 'APP-002',
                dealId: 'DEAL-004',
                recommendation: 'Offer 10% discount to close Enterprise Corp deal',
                impact: '$200,000 potential revenue',
                riskLevel: 'Medium',
                reasoning: 'Competitor pricing pressure detected',
                timestamp: '1 hour ago'
            }
        ];
        
        // Remove the approved request
        approvals = approvals.filter(approval => approval.id !== approvalId);
        localStorage.setItem('aaroApprovals', JSON.stringify(approvals));
        
        // Store in approved history
        let approvedHistory = JSON.parse(localStorage.getItem('aaroApprovedHistory') || '[]');
        const approvedItem = {
            id: approvalId,
            status: 'approved',
            timestamp: new Date().toISOString(),
            approvedBy: 'Current User'
        };
        approvedHistory.push(approvedItem);
        localStorage.setItem('aaroApprovedHistory', JSON.stringify(approvedHistory));
        
        alert(`Request ${approvalId} approved successfully!`);
        
        // Refresh the approvals page
        window.aaroApp.loadApprovals();
    } catch (error) {
        console.error('Error approving request:', error);
        alert('Error approving request. Please try again.');
    }
};

window.rejectRequest = (approvalId) => {
    console.log(`Rejecting request ${approvalId}`);
    
    try {
        // Get current approvals from localStorage or use mock data
        let approvals = JSON.parse(localStorage.getItem('aaroApprovals') || 'null') || [
            {
                id: 'APP-001',
                dealId: 'DEAL-002',
                recommendation: 'Schedule urgent call with TechStart Inc decision maker',
                impact: '$75,000 deal at risk',
                riskLevel: 'High',
                reasoning: 'Deal stalled for 21 days with no scheduled next action',
                timestamp: '15 minutes ago'
            },
            {
                id: 'APP-002',
                dealId: 'DEAL-004',
                recommendation: 'Offer 10% discount to close Enterprise Corp deal',
                impact: '$200,000 potential revenue',
                riskLevel: 'Medium',
                reasoning: 'Competitor pricing pressure detected',
                timestamp: '1 hour ago'
            }
        ];
        
        // Remove the rejected request
        approvals = approvals.filter(approval => approval.id !== approvalId);
        localStorage.setItem('aaroApprovals', JSON.stringify(approvals));
        
        // Store in rejected history
        let rejectedHistory = JSON.parse(localStorage.getItem('aaroRejectedHistory') || '[]');
        const rejectedItem = {
            id: approvalId,
            status: 'rejected',
            timestamp: new Date().toISOString(),
            rejectedBy: 'Current User'
        };
        rejectedHistory.push(rejectedItem);
        localStorage.setItem('aaroRejectedHistory', JSON.stringify(rejectedHistory));
        
        alert(`Request ${approvalId} rejected successfully!`);
        
        // Refresh the approvals page
        window.aaroApp.loadApprovals();
    } catch (error) {
        console.error('Error rejecting request:', error);
        alert('Error rejecting request. Please try again.');
    }
};

window.escalateRequest = (approvalId) => {
    console.log(`Escalating request ${approvalId}`);
    
    try {
        // Get current approvals
        let approvals = JSON.parse(localStorage.getItem('aaroApprovals') || 'null') || [
            {
                id: 'APP-001',
                dealId: 'DEAL-002',
                recommendation: 'Schedule urgent call with TechStart Inc decision maker',
                impact: '$75,000 deal at risk',
                riskLevel: 'High',
                reasoning: 'Deal stalled for 21 days with no scheduled next action',
                timestamp: '15 minutes ago'
            },
            {
                id: 'APP-002',
                dealId: 'DEAL-004',
                recommendation: 'Offer 10% discount to close Enterprise Corp deal',
                impact: '$200,000 potential revenue',
                riskLevel: 'Medium',
                reasoning: 'Competitor pricing pressure detected',
                timestamp: '1 hour ago'
            }
        ];
        
        // Update the approval to escalated status
        const approvalIndex = approvals.findIndex(approval => approval.id === approvalId);
        if (approvalIndex !== -1) {
            approvals[approvalIndex].status = 'escalated';
            approvals[approvalIndex].escalatedAt = new Date().toISOString();
            localStorage.setItem('aaroApprovals', JSON.stringify(approvals));
        }
        
        alert(`Request ${approvalId} escalated to senior management!`);
        
        // Refresh the approvals page
        window.aaroApp.loadApprovals();
    } catch (error) {
        console.error('Error escalating request:', error);
        alert('Error escalating request. Please try again.');
    }
};

// Form handling functions
window.showAddDealForm = () => {
    document.getElementById('add-deal-form').style.display = 'block';
};

window.hideAddDealForm = () => {
    document.getElementById('add-deal-form').style.display = 'none';
    clearDealForm();
};

window.saveDeal = async () => {
    const dealData = {
        id: 'DEAL-' + Date.now(), // Generate unique ID
        company: document.getElementById('deal-company').value,
        value: '$' + document.getElementById('deal-value').value,
        stage: document.getElementById('deal-stage').value,
        rep: document.getElementById('deal-rep').value,
        contact: document.getElementById('deal-contact').value,
        email: document.getElementById('deal-email').value,
        phone: document.getElementById('deal-phone').value,
        closeDate: document.getElementById('deal-close-date').value,
        notes: document.getElementById('deal-notes').value,
        created: new Date().toISOString().split('T')[0]
    };

    if (!dealData.company || !dealData.value || !dealData.stage || !dealData.rep) {
        alert('Please fill in all required fields');
        return;
    }

    try {
        // Save to localStorage
        let deals = JSON.parse(localStorage.getItem('aaroDeals') || '[]');
        deals.push(dealData);
        localStorage.setItem('aaroDeals', JSON.stringify(deals));
        
        console.log('Saving deal:', dealData);
        alert('Deal saved successfully!');
        hideAddDealForm();
        window.aaroApp.loadDealsData();
    } catch (error) {
        alert('Error saving deal: ' + error.message);
    }
};

window.showAddPlaybookForm = () => {
    document.getElementById('add-playbook-form').style.display = 'block';
};

window.hideAddPlaybookForm = () => {
    document.getElementById('add-playbook-form').style.display = 'none';
    clearPlaybookForm();
};

window.savePlaybook = async () => {
    const playbookData = {
        id: 'PB-' + Date.now(), // Generate unique ID
        title: document.getElementById('playbook-title').value,
        category: document.getElementById('playbook-category').value,
        content: document.getElementById('playbook-content').value,
        tags: document.getElementById('playbook-tags').value.split(',').map(tag => tag.trim()).filter(tag => tag),
        created: new Date().toISOString().split('T')[0]
    };

    if (!playbookData.title || !playbookData.category || !playbookData.content) {
        alert('Please fill in all required fields');
        return;
    }

    try {
        // Save to localStorage
        let playbooks = JSON.parse(localStorage.getItem('aaroPlaybooks') || '[]');
        playbooks.push(playbookData);
        localStorage.setItem('aaroPlaybooks', JSON.stringify(playbooks));
        
        console.log('Saving playbook:', playbookData);
        alert('Playbook saved successfully!');
        hideAddPlaybookForm();
        window.aaroApp.loadPlaybooksData();
    } catch (error) {
        alert('Error saving playbook: ' + error.message);
    }
};

window.showAddRepForm = () => {
    document.getElementById('add-rep-form').style.display = 'block';
};

window.hideAddRepForm = () => {
    document.getElementById('add-rep-form').style.display = 'none';
    clearRepForm();
};

window.saveRep = async () => {
    const repData = {
        id: 'REP-' + Date.now(), // Generate unique ID
        name: document.getElementById('rep-name').value,
        email: document.getElementById('rep-email').value,
        role: document.getElementById('rep-role').value,
        territory: document.getElementById('rep-territory').value,
        quota: '$' + document.getElementById('rep-quota').value,
        manager: document.getElementById('rep-manager').value,
        created: new Date().toISOString().split('T')[0]
    };

    if (!repData.name || !repData.email || !repData.role) {
        alert('Please fill in all required fields');
        return;
    }

    try {
        // Save to localStorage
        let team = JSON.parse(localStorage.getItem('aaroTeam') || '[]');
        team.push(repData);
        localStorage.setItem('aaroTeam', JSON.stringify(team));
        
        console.log('Saving rep:', repData);
        alert('Sales rep saved successfully!');
        hideAddRepForm();
        window.aaroApp.loadTeamData();
    } catch (error) {
        alert('Error saving rep: ' + error.message);
    }
};

window.showAddRuleForm = () => {
    document.getElementById('add-rule-form').style.display = 'block';
};

window.hideAddRuleForm = () => {
    document.getElementById('add-rule-form').style.display = 'none';
    clearRuleForm();
};

window.saveRule = async () => {
    const ruleData = {
        id: 'RULE-' + Date.now(), // Generate unique ID
        name: document.getElementById('rule-name').value,
        category: document.getElementById('rule-category').value,
        trigger: document.getElementById('rule-trigger').value,
        threshold: document.getElementById('rule-threshold').value,
        action: document.getElementById('rule-action').value,
        description: document.getElementById('rule-description').value,
        active: true,
        created: new Date().toISOString().split('T')[0]
    };

    if (!ruleData.name || !ruleData.category || !ruleData.trigger || !ruleData.action) {
        alert('Please fill in all required fields');
        return;
    }

    try {
        // Save to localStorage
        let rules = JSON.parse(localStorage.getItem('aaroRules') || '[]');
        rules.push(ruleData);
        localStorage.setItem('aaroRules', JSON.stringify(rules));
        
        console.log('Saving rule:', ruleData);
        alert('AI rule saved successfully!');
        hideAddRuleForm();
        window.aaroApp.loadAIRulesData();
    } catch (error) {
        alert('Error saving rule: ' + error.message);
    }
};

// CRM and Settings functions
window.testCRMConnection = async () => {
    const crmType = document.getElementById('crm-type').value;
    const crmUrl = document.getElementById('crm-url').value;
    
    try {
        console.log('Testing CRM connection:', { crmType, crmUrl });
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 2000));
        alert('CRM connection successful!');
    } catch (error) {
        alert('CRM connection failed: ' + error.message);
    }
};

window.saveCRMConfig = async () => {
    const config = {
        type: document.getElementById('crm-type').value,
        url: document.getElementById('crm-url').value,
        username: document.getElementById('crm-username').value,
        token: document.getElementById('crm-token').value,
        syncDeals: document.getElementById('sync-deals').checked,
        syncActivities: document.getElementById('sync-activities').checked,
        syncContacts: document.getElementById('sync-contacts').checked,
        syncPerformance: document.getElementById('sync-performance').checked,
        syncFrequency: document.getElementById('sync-frequency').value
    };

    try {
        console.log('Saving CRM config:', config);
        alert('CRM configuration saved successfully!');
    } catch (error) {
        alert('Error saving CRM config: ' + error.message);
    }
};

window.saveNotificationSettings = async () => {
    const settings = {
        emailHighRisk: document.getElementById('email-high-risk').checked,
        emailApprovals: document.getElementById('email-approvals').checked,
        emailDailySummary: document.getElementById('email-daily-summary').checked,
        slackWebhook: document.getElementById('slack-webhook').value,
        slackAlerts: document.getElementById('slack-alerts').checked,
        highRiskThreshold: document.getElementById('high-risk-threshold').value,
        stalledDays: document.getElementById('stalled-days').value
    };

    try {
        console.log('Saving notification settings:', settings);
        alert('Notification settings saved successfully!');
    } catch (error) {
        alert('Error saving settings: ' + error.message);
    }
};

window.saveSystemSettings = async () => {
    const settings = {
        confidenceThreshold: document.getElementById('ai-confidence-threshold').value,
        autoExecuteLowRisk: document.getElementById('auto-execute-low-risk').checked,
        requireApprovalHighValue: document.getElementById('require-approval-high-value').checked,
        logRetention: document.getElementById('log-retention').value
    };

    try {
        console.log('Saving system settings:', settings);
        alert('System settings saved successfully!');
    } catch (error) {
        alert('Error saving settings: ' + error.message);
    }
};

window.resetToDefaults = () => {
    if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
        // Reset form values to defaults
        document.getElementById('ai-confidence-threshold').value = 80;
        document.getElementById('confidence-value').textContent = '80%';
        document.getElementById('auto-execute-low-risk').checked = true;
        document.getElementById('require-approval-high-value').checked = false;
        document.getElementById('log-retention').value = 90;
        alert('Settings reset to defaults');
    }
};

// Edit and delete functions
window.editDeal = (dealId) => {
    console.log('Editing deal:', dealId);
    // For now, show an alert - in production this would open an edit form
    alert(`Edit functionality for deal ${dealId} would open an edit form here. This is a demo - the deal data is currently mock data.`);
};

window.deleteDeal = (dealId) => {
    if (confirm('Are you sure you want to delete this deal?')) {
        console.log('Deleting deal:', dealId);
        
        try {
            // Remove from localStorage
            let deals = JSON.parse(localStorage.getItem('aaroDeals') || '[]');
            deals = deals.filter(deal => deal.id !== dealId);
            localStorage.setItem('aaroDeals', JSON.stringify(deals));
            
            console.log(`Deal ${dealId} deleted successfully`);
            alert(`Deal ${dealId} has been deleted successfully!`);
            
            // Refresh the deals list
            window.aaroApp.loadDealsData();
        } catch (error) {
            console.error('Error deleting deal:', error);
            alert('Error deleting deal. Please try again.');
        }
    }
};

window.editPlaybook = (playbookId) => {
    console.log('Editing playbook:', playbookId);
    alert(`Edit functionality for playbook ${playbookId} would open an edit form here. This is a demo - the playbook data is currently mock data.`);
};

window.deletePlaybook = (playbookId) => {
    if (confirm('Are you sure you want to delete this playbook?')) {
        console.log('Deleting playbook:', playbookId);
        
        try {
            // Remove from localStorage
            let playbooks = JSON.parse(localStorage.getItem('aaroPlaybooks') || '[]');
            playbooks = playbooks.filter(playbook => playbook.id !== playbookId);
            localStorage.setItem('aaroPlaybooks', JSON.stringify(playbooks));
            
            console.log(`Playbook ${playbookId} deleted successfully`);
            alert(`Playbook ${playbookId} has been deleted successfully!`);
            
            // Refresh the playbooks list
            window.aaroApp.loadPlaybooksData();
        } catch (error) {
            console.error('Error deleting playbook:', error);
            alert('Error deleting playbook. Please try again.');
        }
    }
};

window.editRep = (repId) => {
    console.log('Editing rep:', repId);
    alert(`Edit functionality for sales rep ${repId} would open an edit form here. This is a demo - the rep data is currently mock data.`);
};

window.deleteRep = (repId) => {
    if (confirm('Are you sure you want to delete this sales rep?')) {
        console.log('Deleting rep:', repId);
        
        try {
            // Remove from localStorage
            let team = JSON.parse(localStorage.getItem('aaroTeam') || '[]');
            team = team.filter(rep => rep.id !== repId);
            localStorage.setItem('aaroTeam', JSON.stringify(team));
            
            console.log(`Sales rep ${repId} deleted successfully`);
            alert(`Sales rep ${repId} has been deleted successfully!`);
            
            // Refresh the team list
            window.aaroApp.loadTeamData();
        } catch (error) {
            console.error('Error deleting sales rep:', error);
            alert('Error deleting sales rep. Please try again.');
        }
    }
};

window.editRule = (ruleId) => {
    console.log('Editing rule:', ruleId);
    alert(`Edit functionality for AI rule ${ruleId} would open an edit form here. This is a demo - the rule data is currently mock data.`);
};

window.deleteRule = (ruleId) => {
    if (confirm('Are you sure you want to delete this rule?')) {
        console.log('Deleting rule:', ruleId);
        
        try {
            // Remove from localStorage
            let rules = JSON.parse(localStorage.getItem('aaroRules') || '[]');
            rules = rules.filter(rule => rule.id !== ruleId);
            localStorage.setItem('aaroRules', JSON.stringify(rules));
            
            console.log(`AI rule ${ruleId} deleted successfully`);
            alert(`AI rule ${ruleId} has been deleted successfully!`);
            
            // Refresh the rules list
            window.aaroApp.loadAIRulesData();
        } catch (error) {
            console.error('Error deleting AI rule:', error);
            alert('Error deleting AI rule. Please try again.');
        }
    }
};

window.toggleRule = (ruleId) => {
    console.log('Toggling rule:', ruleId);
    // Implement rule toggle
};

// Form clearing functions
function clearDealForm() {
    document.getElementById('deal-company').value = '';
    document.getElementById('deal-value').value = '';
    document.getElementById('deal-stage').value = '';
    document.getElementById('deal-rep').value = '';
    document.getElementById('deal-contact').value = '';
    document.getElementById('deal-email').value = '';
    document.getElementById('deal-phone').value = '';
    document.getElementById('deal-close-date').value = '';
    document.getElementById('deal-notes').value = '';
}

function clearPlaybookForm() {
    document.getElementById('playbook-title').value = '';
    document.getElementById('playbook-category').value = '';
    document.getElementById('playbook-content').value = '';
    document.getElementById('playbook-tags').value = '';
}

function clearRepForm() {
    document.getElementById('rep-name').value = '';
    document.getElementById('rep-email').value = '';
    document.getElementById('rep-role').value = '';
    document.getElementById('rep-territory').value = '';
    document.getElementById('rep-quota').value = '';
    document.getElementById('rep-manager').value = '';
}

function clearRuleForm() {
    document.getElementById('rule-name').value = '';
    document.getElementById('rule-category').value = '';
    document.getElementById('rule-trigger').value = '';
    document.getElementById('rule-threshold').value = '';
    document.getElementById('rule-action').value = '';
    document.getElementById('rule-description').value = '';
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    window.aaroApp = new AAROApp();
});

// Add CSS for additional components
const additionalCSS = `
.decision-card {
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.decision-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.decision-type {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--primary-color);
    text-transform: uppercase;
}

.decision-status {
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: var(--font-size-xs);
    font-weight: 600;
    text-transform: uppercase;
}

.decision-status.executed {
    background-color: #f0fdf4;
    color: var(--success-color);
}

.decision-status.pending-approval {
    background-color: #fffbeb;
    color: var(--warning-color);
}

.decision-content h4 {
    margin-bottom: 0.5rem;
    color: var(--gray-900);
}

.decision-meta {
    display: flex;
    justify-content: space-between;
    font-size: var(--font-size-sm);
    color: var(--gray-500);
    margin-top: 1rem;
}

.approval-card {
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-bottom: 1rem;
    border-left: 4px solid var(--warning-color);
}

.approval-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.approval-id {
    font-weight: 600;
    color: var(--gray-900);
}

.risk-level {
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: var(--font-size-xs);
    font-weight: 600;
    text-transform: uppercase;
}

.risk-level.high {
    background-color: #fef2f2;
    color: var(--danger-color);
}

.risk-level.medium {
    background-color: #fffbeb;
    color: var(--warning-color);
}

.approval-details {
    margin: 1rem 0;
}

.detail-row {
    margin-bottom: 0.5rem;
    font-size: var(--font-size-sm);
}

.approval-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
}

.log-entry {
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: var(--border-radius);
    padding: 1rem;
    margin-bottom: 0.5rem;
}

.log-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.log-type {
    font-weight: 600;
    color: var(--primary-color);
    font-size: var(--font-size-sm);
}

.log-status.success {
    color: var(--success-color);
    font-weight: 600;
    font-size: var(--font-size-sm);
}

.log-timestamp {
    color: var(--gray-500);
    font-size: var(--font-size-sm);
}

.log-description {
    font-weight: 500;
    margin-bottom: 0.25rem;
}

.log-outcome {
    color: var(--gray-600);
    font-size: var(--font-size-sm);
}

.audit-entry {
    display: grid;
    grid-template-columns: 150px 120px 120px 1fr;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--gray-200);
    font-size: var(--font-size-sm);
}

.audit-timestamp {
    color: var(--gray-500);
}

.audit-user {
    font-weight: 500;
}

.audit-action {
    color: var(--primary-color);
    font-weight: 500;
}

.deal-details {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.detail-section h4 {
    margin-bottom: 1rem;
    color: var(--gray-900);
    border-bottom: 1px solid var(--gray-200);
    padding-bottom: 0.5rem;
}

.detail-grid {
    display: grid;
    gap: 0.75rem;
}

.detail-item {
    display: flex;
    justify-content: space-between;
}

.detail-item label {
    font-weight: 500;
    color: var(--gray-600);
}

.confidence-score {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
}

.confidence-bar {
    flex: 1;
    height: 8px;
    background-color: var(--gray-200);
    border-radius: 4px;
    overflow: hidden;
}

.confidence-fill {
    height: 100%;
    background-color: var(--success-color);
    transition: width 0.3s ease;
}

.risk-factors ul,
.sop-violations ul {
    margin-left: 1rem;
    margin-top: 0.5rem;
}

.risk-factors li,
.sop-violations li {
    margin-bottom: 0.25rem;
    color: var(--gray-600);
}

.recommended-actions {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.action-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background-color: var(--gray-50);
    border-radius: var(--border-radius);
}

.action-priority {
    width: 24px;
    height: 24px;
    background-color: var(--primary-color);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--font-size-sm);
    font-weight: 600;
    flex-shrink: 0;
}

.action-text {
    flex: 1;
    font-size: var(--font-size-sm);
}

.btn-sm {
    padding: 0.375rem 0.75rem;
    font-size: var(--font-size-xs);
}

/* Data Management Styles */
.data-management-tabs,
.config-tabs {
    display: flex;
    border-bottom: 1px solid var(--gray-200);
    margin-bottom: 2rem;
}

.tab-btn {
    padding: 0.75rem 1.5rem;
    border: none;
    background: none;
    color: var(--gray-600);
    font-weight: 500;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s ease;
}

.tab-btn:hover {
    color: var(--primary-color);
}

.tab-btn.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

/* Form Styles */
.input-form {
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: var(--border-radius);
    padding: 2rem;
    margin-bottom: 2rem;
}

.form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
    margin-bottom: 1rem;
}

.form-group {
    display: flex;
    flex-direction: column;
}

.form-group.full-width {
    grid-column: 1 / -1;
}

.form-group label {
    font-weight: 500;
    color: var(--gray-700);
    margin-bottom: 0.5rem;
}

.form-group input,
.form-group select,
.form-group textarea {
    padding: 0.75rem;
    border: 1px solid var(--gray-300);
    border-radius: var(--border-radius);
    font-size: var(--font-size-sm);
    transition: border-color 0.2s ease;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-actions {
    display: flex;
    gap: 1rem;
    justify-content: flex-end;
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--gray-200);
}

/* Data Lists */
.deals-list,
.playbooks-list,
.team-list,
.rules-list {
    display: grid;
    gap: 1rem;
}

.deal-item,
.playbook-item,
.team-item,
.rule-item {
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: var(--border-radius);
    padding: 1.5rem;
}

.deal-header,
.playbook-header,
.team-header,
.rule-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.deal-header h5,
.playbook-header h5,
.team-header h5,
.rule-header h5 {
    margin: 0;
    color: var(--gray-900);
}

.deal-value {
    font-weight: 600;
    color: var(--success-color);
}

.playbook-category,
.team-role {
    background-color: var(--gray-100);
    color: var(--gray-700);
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: var(--font-size-xs);
    font-weight: 500;
}

.deal-details,
.team-details,
.rule-details {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1rem;
    font-size: var(--font-size-sm);
    color: var(--gray-600);
}

.playbook-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.tag {
    background-color: var(--primary-color);
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-size: var(--font-size-xs);
}

.deal-actions,
.playbook-actions,
.team-actions,
.rule-actions {
    display: flex;
    gap: 0.5rem;
}

/* Toggle Switch */
.toggle-switch {
    position: relative;
    display: inline-block;
    width: 50px;
    height: 24px;
}

.toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--gray-300);
    transition: 0.4s;
    border-radius: 24px;
}

.toggle-slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.4s;
    border-radius: 50%;
}

input:checked + .toggle-slider {
    background-color: var(--primary-color);
}

input:checked + .toggle-slider:before {
    transform: translateX(26px);
}

/* Configuration Styles */
.crm-config,
.notification-settings,
.system-settings {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.config-section,
.setting-group {
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: var(--border-radius);
    padding: 1.5rem;
}

.config-section h4,
.setting-group h4 {
    margin-bottom: 1rem;
    color: var(--gray-900);
    border-bottom: 1px solid var(--gray-200);
    padding-bottom: 0.5rem;
}

.sync-options {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-size: var(--font-size-sm);
}

.checkbox-label input[type="checkbox"] {
    width: auto;
    margin: 0;
}

/* Range Slider */
input[type="range"] {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: var(--gray-200);
    outline: none;
    -webkit-appearance: none;
}

input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--primary-color);
    cursor: pointer;
}

input[type="range"]::-moz-range-thumb {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--primary-color);
    cursor: pointer;
    border: none;
}

/* Rule Status */
.rule-status {
    display: flex;
    align-items: center;
}

/* Responsive Design */
@media (max-width: 768px) {
    .form-grid {
        grid-template-columns: 1fr;
    }
    
    .form-actions {
        flex-direction: column;
    }
    
    .data-management-tabs,
    .config-tabs {
        flex-wrap: wrap;
    }
    
    .deal-details,
    .team-details,
    .rule-details {
        flex-direction: column;
        gap: 0.5rem;
    }
}
`;

// Inject additional CSS
const style = document.createElement('style');
style.textContent = additionalCSS;
document.head.appendChild(style);