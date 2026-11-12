import { createRouter, createWebHashHistory } from "vue-router";

// D-18 路由：6 页（首页=视图①）。无登录/无受保护页（任务拆解 §5：单角色、无鉴权），
// 路由守卫不适用属设计性决策，不引入守卫循环风险。
// hash 路由：T26 静态托管下无需服务端回退配置。
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: "/",
      name: "heatmap",
      component: () => import("../views/ProjectHeatmapView.vue"),
    },
    {
      path: "/rework",
      name: "rework",
      component: () => import("../views/ReworkTopView.vue"),
    },
    {
      path: "/root-cause",
      name: "root-cause",
      component: () => import("../views/RootCauseView.vue"),
    },
    {
      path: "/gate-trend",
      name: "gate-trend",
      component: () => import("../views/GateTrendView.vue"),
    },
    {
      path: "/compare",
      name: "compare",
      component: () => import("../views/CrossCompareView.vue"),
    },
    {
      path: "/reconcile",
      name: "reconcile",
      component: () => import("../views/ReconcileView.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

export default router;
