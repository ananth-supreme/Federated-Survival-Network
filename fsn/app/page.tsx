"use client";

import React, { useEffect, useState, useMemo } from 'react';
import { Shield, Radio, Target, Activity, Zap, Cpu, Wifi } from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  ScatterChart, Scatter, ZAxis, ReferenceLine, Cell
} from 'recharts';

const API_URL = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

export default function Dashboard() {
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [latestTelemetry, setLatestTelemetry] = useState([]);
  const [events, setEvents] = useState([]);
  const [islLinks, setIslLinks] = useState([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => setConnected(true);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const sortedLatest = data.telemetry.sort((a, b) => a.satellite_id - b.satellite_id);
      setLatestTelemetry(sortedLatest);
      setTelemetryHistory(prev => {
        const newHistory = [...prev, ...data.telemetry];
        if (newHistory.length > 900) return newHistory.slice(newHistory.length - 900);
        return newHistory;
      });
      setEvents(data.events);
      if (data.isl) setIslLinks(data.isl);
    };
    ws.onclose = () => setConnected(false);
    return () => ws.close();
  }, []);

  const satAHistory = useMemo(() => 
    telemetryHistory.filter(t => t.satellite_id === 1), 
  [telemetryHistory]);

  const trails = useMemo(() => {
    const result = { 1: [], 2: [], 3: [] };
    telemetryHistory.forEach(t => {
      if (!result[t.satellite_id]) return;
      const arr = result[t.satellite_id];
      const last = arr[arr.length - 1];
      const moved = !last
        || Math.hypot(t.pos_y - last.pos_y, t.pos_z - last.pos_z) > 3;
      if (moved) {
        arr.push(t);
        if (arr.length > 30) arr.shift();
      }
    });
    return result;
  }, [telemetryHistory]);

  const targetFormation = [
    { pos_y: 0, pos_z: 0 },
    { pos_y: 250, pos_z: 433 },
    { pos_y: -250, pos_z: 433 },
    { pos_y: 0, pos_z: 0 },
  ];

  const injectFault = async () => {
    try {
      const resp = await fetch(`${API_URL}/commands`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issued_at: Date.now() / 1000, command_type: "INJECT_FAULT", status: "PENDING" })
      });
      if (resp.ok) alert("CRITICAL: Fault Injection Sequence Started");
    } catch (e) { alert("Error: " + e.message); }
  };

  const resetSim = async () => {
    try {
      await fetch(`${API_URL}/commands`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issued_at: Date.now() / 1000, command_type: "RESET", status: "PENDING" })
      });
      setTelemetryHistory([]);
      setLatestTelemetry([]);
      setEvents([]);
      alert("SYSTEM RESET: Restoring nominal orbit...");
    } catch (e) { alert("Error: " + e.message); }
  };

  return (
    <div className="min-h-screen bg-[#05070a] text-[#E8EDF8] p-10 font-mono selection:bg-blue-500/30 text-xl">
      {/* Header */}
      <header className="flex justify-between items-center mb-12 border-b-2 border-[#1E2D50] pb-8 bg-[#111827]/30 p-6 rounded-t-2xl">
        <div className="flex items-center gap-8">
          <div className="p-4 bg-blue-500/10 rounded-2xl border-2 border-blue-500/20 shadow-[0_0_20px_rgba(59,130,246,0.15)]">
            <Shield className="text-blue-400" size={52} />
          </div>
          <div>
            <h1 className="text-4xl font-black tracking-tightest text-white uppercase">Federated Survival Network</h1>
            <p className="text-blue-400/70 text-lg tracking-[0.4em] font-bold mt-2">DECENTRALIZED RECOVERY CONSOLE // V3.2-REFINED</p>
          </div>
        </div>
        <div className="flex items-center gap-10">
          <div className="text-right border-r-2 border-[#1E2D50] pr-10">
            <p className="text-xs font-black text-slate-500 uppercase tracking-widest mb-2">Network Health</p>
            <p className={`text-2xl font-black ${connected ? 'text-[#10B981]' : 'text-red-500'}`}>
              {connected ? '● LINK SECURE' : '○ NO SIGNAL'}
            </p>
          </div>
          <div className="flex gap-6">
            <button 
              onClick={injectFault}
              className="bg-red-500/10 hover:bg-red-500/20 text-red-500 border-2 border-red-500/40 px-8 py-4 rounded-xl text-base font-black transition-all flex items-center gap-3 shadow-[0_0_30px_rgba(239,68,68,0.1)] active:scale-95 uppercase"
            >
              <Radio size={24} /> Trigger Failure
            </button>
            <button 
              onClick={resetSim}
              className="bg-slate-800 hover:bg-slate-700 text-white border-2 border-slate-600 px-8 py-4 rounded-xl text-base font-black transition-all active:scale-95 uppercase"
            >
              Reset Swarm
            </button>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-10">
        
        {/* Left: Satellite Health */}
        <div className="col-span-3 space-y-8">
          <h2 className="text-sm font-black text-slate-500 uppercase tracking-[0.5em] mb-4 flex items-center gap-3">
            <Cpu size={20} /> Onboard Telemetry
          </h2>
          {latestTelemetry.map((sat) => (
            <div key={sat.satellite_id} className={`bg-[#111827] border-2 rounded-2xl overflow-hidden transition-all duration-500 p-8 ${sat.fault_active && sat.attitude_error_deg > 0.5 ? 'border-red-500/50 shadow-[0_0_40px_rgba(239,68,68,0.2)]' : sat.sensor_source === 'PHANTOM' ? 'border-amber-500/40 shadow-[0_0_30px_rgba(245,158,11,0.15)]' : 'border-[#1E2D50] hover:border-blue-500/30'}`}>
              <div className="flex justify-between items-center mb-8">
                <div>
                  <h3 className="text-2xl font-black tracking-widest text-blue-400 uppercase">SAT-{String.fromCharCode(64 + sat.satellite_id)}</h3>
                  <p className="text-xs font-bold text-slate-500 mt-2 uppercase tracking-tighter">LEO SWARM • {sat.role}</p>
                </div>
                <div className={`px-4 py-2 rounded-lg text-xs font-black tracking-widest border-2 ${
                  sat.sensor_source === 'PHYSICAL' ? 'bg-green-500/10 text-green-500 border-green-500/30' : 
                  sat.sensor_source === 'PHANTOM' ? 'bg-amber-500/10 text-amber-500 border-amber-500/30' : 
                  'bg-red-500/10 text-red-500 border-red-500/30'
                }`}>
                  {sat.sensor_source}
                </div>
              </div>
              <div className="space-y-8">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <p className="text-xs font-black text-slate-500 uppercase tracking-widest">Attitude Knowledge Error</p>
                    <p className={`text-2xl font-black tabular-nums ${
                      sat.attitude_error_deg > 0.5 ? 'text-red-500' :
                      sat.sensor_source === 'PHANTOM' ? 'text-amber-400' : 'text-green-500'
                    }`}>
                      {sat.attitude_error_deg.toFixed(4)}°
                    </p>
                  </div>
                  <div className="h-2.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
                    <div 
                      className={`h-full transition-all duration-700 ${sat.attitude_error_deg > 0.5 ? 'bg-red-500' : 'bg-green-500'}`} 
                      style={{ width: `${Math.min(sat.attitude_error_deg * 40, 100)}%` }} 
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-8">
                  <div className="bg-[#05070a] p-4 rounded-xl border border-[#1E2D50]">
                    <p className="text-slate-500 mb-2 uppercase text-[10px] font-black tracking-widest">Fuel</p>
                    <p className="font-black text-white text-lg tabular-nums tracking-tighter italic">48.2m/s</p>
                  </div>
                  <div className="bg-[#05070a] p-4 rounded-xl border border-[#1E2D50]">
                    <p className="text-slate-500 mb-2 uppercase text-[10px] font-black tracking-widest">Power</p>
                    <p className="font-black text-green-400 text-lg tabular-nums tracking-tighter">95.0%</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Center: Tactical Map & Physics */}
        <div className="col-span-6 space-y-10">
          <div className="bg-[#070b14] h-[550px] flex flex-col overflow-hidden relative border-2 border-[#1E2D50] rounded-3xl shadow-2xl">
            <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 px-8 pt-6 pb-4 border-b border-[#1E2D50]/60 shrink-0">
              <div>
                <h2 className="text-sm font-black text-slate-400 uppercase tracking-[0.6em] mb-2 flex items-center gap-3">
                  <Target size={20} className="text-blue-500" /> Formation Tactical Map
                </h2>
                <p className="text-xs font-bold text-blue-500 opacity-60 uppercase tracking-widest italic">Hill-Frame Relative Projection • 1:500m Scale</p>
              </div>
              <div className="flex flex-wrap gap-4 sm:gap-6 text-[10px] sm:text-[11px] font-black bg-[#111827]/90 px-4 py-3 rounded-xl border border-[#1E2D50] backdrop-blur-md self-start sm:self-auto">
                <span className="flex items-center gap-2 text-green-400"><div className="w-2.5 h-2.5 rounded-full bg-green-500 shadow-[0_0_12px_#10B981]" /> NOMINAL</span>
                <span className="flex items-center gap-2 text-amber-500"><div className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_12px_#F59E0B]" /> PHANTOM</span>
                <span className="flex items-center gap-2 text-red-500"><div className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-[0_0_12px_#EF4444]" /> FAILED</span>
                <span className="flex items-center gap-2 text-slate-500"><div className="w-5 h-0.5 border-b-2 border-dashed border-slate-600" /> STATION</span>
              </div>
            </div>

            <div className="flex-1 w-full bg-[#05070a] relative min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 24, right: 48, bottom: 48, left: 48 }}>
                  <CartesianGrid strokeDasharray="4 4" stroke="#1E2D50" vertical={true} />
                  <XAxis type="number" dataKey="pos_y" hide domain={[-600, 600]} />
                  <YAxis type="number" dataKey="pos_z" hide domain={[-600, 600]} />
                  <ZAxis type="number" range={[250, 250]} />
                  
                  <Scatter data={targetFormation} line={{ stroke: '#1E2D50', strokeWidth: 3, strokeDasharray: '12 12' }} shape={() => null} />
                  
                  {[1, 2, 3].map(id => (
                    <Scatter 
                      key={`trail-${id}`} 
                      data={trails[id]} 
                      line={{ stroke: id === 1 ? '#EF4444' : '#10B981', strokeWidth: 3, opacity: 0.15 }} 
                      shape={() => null} 
                    />
                  ))}

                  <Scatter name="Satellites" data={latestTelemetry}>
                    {latestTelemetry.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={
                        entry.sensor_source === 'PHYSICAL' ? '#10B981' : 
                        entry.sensor_source === 'PHANTOM' ? '#F59E0B' : '#EF4444'
                      } className={entry.fault_active ? 'animate-pulse' : ''} />
                    ))}
                  </Scatter>
                  
                  <Tooltip 
                    cursor={false}
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-[#111827] border-2 border-[#1E2D50] p-4 rounded-xl shadow-2xl backdrop-blur-lg">
                            <p className="font-black text-blue-400 mb-2 uppercase text-base tracking-widest tracking-tighter">SAT_{String.fromCharCode(64 + data.satellite_id)}</p>
                            <div className="space-y-1 text-slate-300 font-bold text-xs tabular-nums">
                              <p>Y: {data.pos_y.toFixed(2)}m</p>
                              <p>Z: {data.pos_z.toFixed(2)}m</p>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                </ScatterChart>
              </ResponsiveContainer>
              {/* Sight Lines */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 border-2 border-blue-500/5 rounded-full pointer-events-none" />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 border-2 border-blue-500/5 rounded-full pointer-events-none" />
            </div>
          </div>

          {/* Bottom Graph */}
          <div className="bg-[#111827] h-[320px] flex flex-col relative overflow-hidden p-8 border-2 border-[#1E2D50] rounded-3xl shadow-xl">
            <div className="flex justify-between items-start mb-8">
              <div>
                <h2 className="text-sm font-black text-slate-400 uppercase tracking-[0.5em] mb-2 flex items-center gap-3">
                  <Zap size={20} className="text-amber-500" /> Attitude Knowledge Stability
                </h2>
                <p className="text-xs font-bold text-blue-400 opacity-60 uppercase tracking-widest mt-1 italic">Real-Time Knowledge Variance vs. Safety Threshold</p>
              </div>
              <div className="flex gap-10 text-xs font-black tracking-widest uppercase">
                <span className="flex items-center gap-3 text-red-500"><div className="w-6 h-1 bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]" /> Hardware Error</span>
                <span className="flex items-center gap-3 text-amber-500"><div className="w-6 h-2 bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]" /> PSP Virtual Fix</span>
              </div>
            </div>
            
            <div className="flex-1 w-full -ml-6">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={satAHistory}>
                  <CartesianGrid strokeDasharray="4 4" stroke="#1E2D50" vertical={false} />
                  <XAxis dataKey="sim_time_s" hide />
                  <YAxis stroke="#8A99BB" fontSize={12} domain={[0, 3]} tickFormatter={(val) => `${val}°`} tabularNums />
                  <Tooltip contentStyle={{ backgroundColor: '#111827', border: '2px solid #1E2D50', borderRadius: '12px', fontSize: '14px', fontWeight: 'bold' }} />
                  <ReferenceLine y={0.5} stroke="#F59E0B" strokeDasharray="8 8" label={{ value: 'CRITICAL SUCCESS THRESHOLD', position: 'insideTopRight', fill: '#F59E0B', fontSize: 11, fontWeight: '900' }} />
                  <Line type="monotone" dataKey="attitude_error_deg" stroke="#EF4444" strokeWidth={3} dot={false} isAnimationActive={false} name="Knowledge Error" />
                  <Line type="monotone" dataKey="psp_attitude_error_deg" stroke="#F59E0B" strokeWidth={4} dot={false} isAnimationActive={false} connectNulls={false} name="PSP Virtual Fix" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Right: Event Log & Mesh */}
        <div className="col-span-3 space-y-10">
          <div className="bg-[#111827] p-8 border-2 border-[#1E2D50] rounded-3xl shadow-xl">
            <h2 className="text-sm font-black text-slate-500 uppercase tracking-[0.5em] mb-8 flex items-center gap-3">
              <Wifi size={20} /> ISL Mesh Link
            </h2>
            <div className="space-y-4">
              {[
                { label: 'A ↔ B', from: 1, to: 2 },
                { label: 'A ↔ C', from: 1, to: 3 },
                { label: 'B ↔ C', from: 2, to: 3 },
              ].map((pair) => {
                const link = islLinks.find(
                  (l) => l.from_sat_id === pair.from && l.to_sat_id === pair.to
                );
                const isPsp = link?.is_psp_link === 1;
                return (
                <div key={pair.label} className="flex items-center justify-between p-5 bg-[#05070a] rounded-2xl border border-[#1E2D50] hover:border-blue-500/50 transition-all cursor-crosshair group shadow-inner">
                  <div className="flex items-center gap-5">
                    <Radio size={20} className={isPsp ? "text-amber-500 group-hover:animate-pulse" : "text-slate-600"} />
                    <span className="text-lg font-black tracking-widest text-white italic">{pair.label}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] font-black text-slate-500 tracking-[0.2em] uppercase">
                      {link ? `${link.range_m.toFixed(1)}m` : 'LINKED'}
                    </span>
                    <div className={`w-2.5 h-2.5 rounded-full ${isPsp ? 'bg-amber-500 shadow-[0_0_12px_#F59E0B]' : 'bg-green-500 shadow-[0_0_12px_#10B981]'}`} />
                  </div>
                </div>
              )})}
            </div>
          </div>

          <div className="bg-[#111827] h-[550px] flex flex-col p-8 border-2 border-[#1E2D50] rounded-3xl shadow-xl">
            <h2 className="text-sm font-black text-slate-500 uppercase tracking-[0.5em] mb-8 flex items-center gap-3">
              <Activity size={20} /> Mission Logs
            </h2>
            <div className="flex-1 overflow-y-auto space-y-6 pr-4 scrollbar-hide">
              {events.map((event) => (
                <div key={event.id} className="border-l-4 border-[#1E2D50] pl-6 relative pb-2 transition-all">
                  <div className={`absolute -left-[10px] top-1.5 w-4 h-4 rounded-full border-4 border-[#111827] ${
                    event.event_type === 'FAULT_DETECTED' ? 'bg-red-500 shadow-[0_0_15px_rgba(239,68,68,0.6)]' : 
                    event.event_type === 'RECOVERY_COMPLETE' || event.event_type === 'ATTITUDE_STABILIZED' ? 'bg-green-500 shadow-[0_0_15px_rgba(16,185,129,0.6)]' : 'bg-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.6)]'
                  }`} />
                  <div className="flex justify-between items-center mb-2">
                    <span className={`font-black text-xs tracking-widest uppercase ${
                      event.event_type === 'FAULT_DETECTED' ? 'text-red-500' : 
                      event.event_type === 'RECOVERY_COMPLETE' || event.event_type === 'ATTITUDE_STABILIZED' ? 'text-green-500' : 'text-amber-500'
                    }`}>
                      {event.event_type.replace('_', ' ')}
                    </span>
                    <span className="text-xs font-black text-slate-600 tabular-nums uppercase tracking-tighter">T+{event.sim_time_s.toFixed(0)}s</span>
                  </div>
                  <p className="text-slate-400 text-sm font-bold leading-relaxed">{event.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      <footer className="mt-12 flex justify-between items-center text-xs font-black text-slate-600 uppercase tracking-[0.8em] opacity-40 bg-[#111827]/10 p-6 rounded-b-2xl border-t border-[#1E2D50]">
        <p>Clohessy-Wiltshire Engine Active</p>
        <p>Wahba-SVD / QUEST Protocol V3.1</p>
        <p>Auth Session: FSN-2026-STABLE</p>
      </footer>
    </div>
  );
}
