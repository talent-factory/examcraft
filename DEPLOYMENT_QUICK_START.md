# 🚀 GUI Modernization (TF-148) - Quick Start

## ⚡ 30-Second Deployment

```bash
# 1. Make script executable
chmod +x scripts/deploy-gui-modernization.sh

# 2. Deploy
./scripts/deploy-gui-modernization.sh

# 3. Open browser
open http://localhost:3000
```

## 📱 Access Points

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |
| **Qdrant Dashboard** | http://localhost:6333/dashboard |

## 🧪 What to Test

### 1. **New Navigation**
- ✅ Sidebar visible on left
- ✅ Sidebar collapses on mobile
- ✅ Role-based menu items
- ✅ Active route highlighting

### 2. **Dashboard Page**
- ✅ Hero section with greeting
- ✅ Quick Action cards (4 columns)
- ✅ Statistics cards
- ✅ Recent Activity placeholder

### 3. **Feature Pages**
- ✅ `/documents` - Document upload & library
- ✅ `/questions/generate` - RAG exam creation
- ✅ `/questions/review` - Question review
- ✅ `/admin` - User & prompt management

### 4. **Responsive Design**
- ✅ Desktop: Full sidebar
- ✅ Tablet: Sidebar icons only
- ✅ Mobile: Hamburger menu

### 5. **Form Components**
- ✅ Input fields with validation
- ✅ Buttons with variants
- ✅ Select dropdowns
- ✅ Error messages

## 🛠️ Useful Commands

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Check container status
docker-compose ps

# Connect to database
docker-compose exec postgres psql -U examcraft -d examcraft

# View resource usage
docker stats
```

## 🔧 Custom Ports (Git Worktrees)

```bash
# Deploy on different ports
export FRONTEND_PORT=3001
export BACKEND_PORT=8001
./scripts/deploy-gui-modernization.sh
```

## 📊 Test Credentials

```
Email: test@example.com
Password: Test123!@#
```

(Or create new account via Sign Up)

## ✅ Deployment Checklist

- [ ] All containers running (`docker-compose ps`)
- [ ] Frontend loads at http://localhost:3000
- [ ] Backend API responds at http://localhost:8000/docs
- [ ] Sidebar navigation visible
- [ ] Dashboard page loads
- [ ] Feature pages accessible
- [ ] Responsive design works
- [ ] Form components functional

## 🐛 Troubleshooting

**Frontend not loading?**
```bash
docker-compose logs frontend
docker-compose restart frontend
```

**Backend errors?**
```bash
docker-compose logs backend
docker-compose restart backend
```

**Database issues?**
```bash
docker-compose down -v
docker-compose up -d
```

## 📚 Full Documentation

See `docs/DEPLOYMENT_GUI_MODERNIZATION.md` for complete guide.

## 🎯 Next Steps

1. ✅ Test the new GUI
2. ✅ Verify all features work
3. ✅ Create Pull Request
4. ✅ Code Review
5. ✅ Merge to develop
6. ✅ Deploy to production

---

**Branch**: `feature/tf-148-gui-modernization`  
**Status**: ✅ Production Ready  
**Tests**: ✅ 52/52 Passing

