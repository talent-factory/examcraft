# 💰 ExamCraft AI - Monetization Strategy

> **Open-Core Freemium SaaS Model with Enterprise Self-Hosting**  
> **Based on Linear Issue TF-116**

[![Status: Planning](https://img.shields.io/badge/Status-Planning-yellow.svg)](https://linear.app/talent-factory/issue/TF-116)
[![Target: €15K MRR](https://img.shields.io/badge/Target-€15K%20MRR-green.svg)](https://linear.app/talent-factory/issue/TF-116)
[![Timeline: Oct 2025 - Jun 2026](https://img.shields.io/badge/Timeline-Oct%202025--Jun%202026-blue.svg)](https://linear.app/talent-factory/issue/TF-116)

---

## 🎯 Executive Summary

ExamCraft AI follows a **three-pillar monetization strategy**:

1. **Open Source (GitHub/GitLab)** - Community building & lead generation
2. **Freemium SaaS (Render.com)** - Primary revenue stream
3. **Self-Hosted Enterprise** - High-value institutional customers

**Year 1 Target**: €15,000 MRR (~€180K ARR)  
**Break-even**: ~€4,000 MRR (40-50 paying customers)  
**Timeline**: October 2025 - June 2026 (9 months)

---

## 💼 Three-Pillar Business Model

### 1. Open Source (GitHub/GitLab) - Community Edition 🌟

**License**: MIT or Apache 2.0  
**Strategy**: Community building, lead generation, brand awareness  
**Timeline**: Launch October 31, 2025

**Features**:

- ✅ Basic document processing (PDF, Markdown)
- ✅ Limited question generation (20 questions/month)
- ✅ Self-hosting capability
- ✅ Core RAG functionality
- ❌ No ChatBot
- ❌ No advanced analytics
- ❌ No priority support

**Target Audience**:

- Hobby projects
- Individual educators
- Universities (self-hosted)
- Open source contributors

**Revenue Model**: Indirect

- Leads for premium tiers
- Community contributions
- Brand awareness
- Developer ecosystem

**Success Metrics**:

- 100+ GitHub stars in first 2 weeks
- 10+ contributors
- 50+ issues/PRs
- Product Hunt: Top 5 Product of the Day

---

### 2. Freemium SaaS (Render.com) 💳

**Platform**: Render.com Hosting  
**Timeline**: Beta launch December 2025, Public launch January 2026

#### Pricing Tiers

**🆓 Free Tier** - Lead Generation

- 5 documents
- 20 questions/month
- 1 user
- Basic features
- Community support
- **Target**: 500 free signups in first 3 months

**🚀 Starter** - €19/month

- 50 documents
- 200 questions/month
- 3 users
- All core features
- Email support
- **Target**: 25 paying customers by Month 6

**💼 Professional** - €49/month

- Unlimited documents
- 1,000 questions/month
- 10 users
- ChatBot feature
- All v1.x features
- Priority email support
- **Target**: 75 paying customers by Month 9

**🏢 Enterprise** - €149/month

- Unlimited everything
- Unlimited users
- Priority support
- SSO integration
- Advanced analytics
- SLA guarantee
- **Target**: 150 paying customers by Month 12

#### Revenue Projections

**Month 1-3**: Open Source Launch

- Community Building
- 0 MRR

**Month 3-6**: Freemium Launch

- 25 paying customers
- **€2,500 MRR** (Break-even)

**Month 6-9**: Growth Phase

- 75 paying customers
- **€7,500 MRR**

**Month 9-12**: Scale

- 150 paying customers
- **€15,000 MRR**

**Average Customer Value**: €35/month (mixed tiers)  
**Conversion Rate**: 5% (free → paid)  
**Churn Rate**: <5% monthly

---

### 3. Self-Hosted Enterprise Edition 🏢

**Timeline**: April-June 2026  
**Target**: First enterprise deal by Q2 2026

**Pricing**:

- **Setup Fee**: €999 (one-time)
- **License**: €99/month per 10 users
- **Support**: €299/year
- **Total Year 1**: €999 + €1,188 + €299 = **€2,486**

**Features**:

- ✅ On-premise deployment (Kubernetes/Docker Compose)
- ✅ SSO/SAML integration
- ✅ LDAP authentication
- ✅ Custom branding
- ✅ SLA guarantee (99.9% uptime)
- ✅ Dedicated support
- ✅ Data sovereignty
- ✅ Air-gapped deployment option

**Target Audience**:

- Large universities (>10,000 students)
- Government institutions
- Compliance-critical organizations
- GDPR-sensitive customers

**Sales Process**:

1. Inbound lead from SaaS tier
2. Discovery call (needs assessment)
3. Technical demo (IT team)
4. Proof of concept (30 days)
5. Contract negotiation
6. Implementation (2-4 weeks)
7. Training & onboarding

---

## 📊 Financial Projections

### Year 1 Revenue Breakdown

| Month | Free Users | Paid Users | MRR | ARR (Projected) |
|-------|------------|------------|-----|-----------------|
| 1-3 | 100 | 0 | €0 | €0 |
| 4 | 200 | 10 | €500 | €6,000 |
| 5 | 300 | 15 | €1,000 | €12,000 |
| 6 | 500 | 25 | €2,500 | €30,000 |
| 7 | 600 | 40 | €4,000 | €48,000 |
| 8 | 700 | 55 | €5,500 | €66,000 |
| 9 | 800 | 75 | €7,500 | €90,000 |
| 10 | 900 | 100 | €10,000 | €120,000 |
| 11 | 1,000 | 125 | €12,500 | €150,000 |
| 12 | 1,200 | 150 | €15,000 | €180,000 |

**First Enterprise Deal**: Month 8-10

- +€999 setup fee
- +€99/month recurring

---

## 💸 Cost Structure (Monthly at Scale)

### Infrastructure Costs

```
Render.com Hosting:        €150-250
Qdrant Cloud:              €100
PostgreSQL:                €50
Redis:                     €30
                           ----------
Subtotal:                  €330-430
```text

### AI & Operations

```
Claude API (150 customers): €300-500
Stripe Fees (3%):          ~€450 (at €15k MRR)
Email Service:             €50
Monitoring Tools:          €100
                           ----------
Subtotal:                  €900-1,100
```text

### Marketing & Growth

```
Content/Ads:               €1,000-2,000
Tools (Analytics):         €200
                           ----------
Subtotal:                  €1,200-2,200
```text

### Support & Miscellaneous

```
Support Tools:             €100
Domain & SSL:              €10
Miscellaneous:             €100
                           ----------
Subtotal:                  €210
```text

**TOTAL MONTHLY COSTS**: €2,640-3,940

**Break-even Point**: ~€4,000 MRR (40-50 paying customers)  
**Profit Margin at €15K MRR**: ~70% (€10,500/month)

---

## 🌐 Domain Strategy

### Current Status

- ❌ **examcraft.ie** is already taken (Irish education tool)
- ⚠️ **.ai domains** cost €75-80/year (minimum 2 years registration)
- ✅ **.io/.com** are cheaper and more established

### Top Recommendations

**Tier 1 - Premium Choices**

1. **examcraft.ai** - Perfect for AI focus, but expensive (~€160 for 2 years)
2. **examcrafter.ai** - Alternative with "Crafter" suffix
3. **craftexam.ai** - Reversed variant

**Tier 2 - Balanced Options**
4. **examcraft.io** - Tech startup standard, cheaper than .ai (~€40/year)
5. **examcrafter.io** - IO variant
6. **getexamcraft.com** - "Get" prefix (like GetStream, GetFeedback)
7. **tryexamcraft.com** - "Try" prefix for trial focus

**Tier 3 - Alternative Names**
8. **examgenai.com** - "ExamGen AI" - short and catchy
9. **aiexamcraft.com** - AI prefix
10. **examcraft-ai.com** - With hyphen

**Final Recommendation**: Check **examcraft.ai** and **examcraft.io** first. If taken, go with **getexamcraft.com** or **examcrafter.ai**.

---

## 📅 Implementation Timeline

### Phase 1: Open Source Preparation (Weeks 1-4)

**Timeline**: October 2025  
**Issue**: [TF-112](https://linear.app/talent-factory/issue/TF-112) - GitHub Release Ready

**Tasks**:

- [ ] Repository cleanup (remove secrets, sensitive data)
- [ ] Complete documentation (README, CONTRIBUTING, CODE_OF_CONDUCT)
- [ ] Add MIT/Apache 2.0 license
- [ ] Create demo video
- [ ] Set up community channels (Discord, Discussions)
- [ ] Prepare Product Hunt launch

**Deliverable**: Open Source Launch by **October 31, 2025**

---

### Phase 2: Freemium SaaS Setup (Weeks 5-10)

**Timeline**: November-December 2025  
**Issue**: [TF-113](https://linear.app/talent-factory/issue/TF-113) - Render.com Deployment with Stripe

**Tasks**:

- [ ] Render.com multi-service setup
- [ ] Stripe payment integration
- [ ] User authentication & authorization
- [ ] Tier-based rate limiting
- [ ] Multi-tenancy architecture
- [ ] Usage tracking & analytics
- [ ] Email notifications (Mailgun/SendGrid)
- [ ] Beta tester onboarding

**Deliverable**: Beta Launch with 100 testers by **December 2025**

---

### Phase 3: Marketing & Acquisition (Parallel to Phase 2)

**Timeline**: December 2025 - January 2026  
**Issue**: [TF-115](https://linear.app/talent-factory/issue/TF-115) - Customer Acquisition

**Tasks**:

- [ ] Landing page design & development
- [ ] SEO optimization
- [ ] Content marketing (blog posts, tutorials)
- [ ] Social media presence (Twitter, LinkedIn)
- [ ] Product Hunt launch
- [ ] Beta program management
- [ ] Email nurture campaigns
- [ ] Webinars & workshops

**Deliverable**: First 25 paying customers by **January 2026**

---

### Phase 4: Enterprise Edition (Month 4-6)

**Timeline**: April-June 2026  
**Issue**: [TF-114](https://linear.app/talent-factory/issue/TF-114) - Self-Hosted Offering

**Tasks**:

- [ ] Kubernetes deployment manifests
- [ ] Docker Compose for simpler deployments
- [ ] SSO/SAML integration (Keycloak, Auth0)
- [ ] LDAP authentication
- [ ] License management system
- [ ] Custom branding options
- [ ] Enterprise sales process
- [ ] Partnership outreach (universities)

**Deliverable**: First enterprise deal by **Q2 2026**

---

## 🎯 Success Criteria

### Phase 1 Success (Open Source)

- ✅ 100+ GitHub stars in first 2 weeks
- ✅ 10+ contributors
- ✅ 50+ issues/PRs
- ✅ Product Hunt: Top 5 Product of the Day

### Phase 2 Success (Freemium SaaS)

- ✅ 500+ free signups in first 3 months
- ✅ 25+ paying customers after 6 months
- ✅ €2,500 MRR (break-even)
- ✅ <5% churn rate
- ✅ NPS >40

### Phase 3 Success (Growth)

- ✅ €15,000 MRR after 12 months
- ✅ 150+ paying customers
- ✅ 1+ enterprise deal
- ✅ Profitable unit economics (LTV:CAC >3:1)

---

## 📞 Related Resources

- **Linear Epic**: [TF-116 - Monetization Strategy](https://linear.app/talent-factory/issue/TF-116)
- **Sub-Tasks**:
  - [TF-112](https://linear.app/talent-factory/issue/TF-112) - Open Source Preparation
  - [TF-113](https://linear.app/talent-factory/issue/TF-113) - Freemium SaaS Setup
  - [TF-114](https://linear.app/talent-factory/issue/TF-114) - Enterprise Edition
  - [TF-115](https://linear.app/talent-factory/issue/TF-115) - Marketing & Acquisition

---

**Last Updated**: January 2025 | **Owner**: Daniel Senften | **Status**: Planning 📋
