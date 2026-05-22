import { Routes, Route } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import PageHeader from "@/components/PageHeader";
import Backdrop from "@/components/Backdrop";
import LiveStatusStrip from "@/components/LiveStatusStrip";
import BrainPage from "@/pages/BrainPage";
import DashboardPage from "@/pages/DashboardPage";
import GraphPage from "@/pages/GraphPage";
import MemoryPage from "@/pages/MemoryPage";
import TasksPage from "@/pages/TasksPage";
import ConductorPage from "@/pages/ConductorPage";
import SessionsPage from "@/pages/SessionsPage";
import RetrievalsPage from "@/pages/RetrievalsPage";
import LearningPage from "@/pages/LearningPage";
import ConsolidationPage from "@/pages/ConsolidationPage";
import UnderstandPage from "@/pages/UnderstandPage";
import SettingsPage from "@/pages/SettingsPage";

export default function App() {
  return (
    <div className="h-full w-full flex bg-[color:var(--background-base)] text-[color:var(--midground-base)] relative">
      <Backdrop />
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <LiveStatusStrip />
        <PageHeader />
        <div className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/brain" element={<BrainPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/conductor" element={<ConductorPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/retrievals" element={<RetrievalsPage />} />
            <Route path="/learning" element={<LearningPage />} />
            <Route path="/consolidation" element={<ConsolidationPage />} />
            <Route path="/understand" element={<UnderstandPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/:section" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
