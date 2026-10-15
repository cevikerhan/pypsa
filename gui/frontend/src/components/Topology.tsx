import React, { useEffect } from 'react';
import ReactFlow, { Background, Controls, MiniMap, Node, Edge } from 'react-flow-renderer';

type TopologyProps = {
  networkId: string;
};

export default function Topology({ networkId }: TopologyProps) {
  const [nodes, setNodes] = React.useState<Node[]>([]);
  const [edges, setEdges] = React.useState<Edge[]>([]);

  useEffect(() => {
    const loadTopology = async () => {
      try {
        const res = await fetch(`/api/network-topology?network=${encodeURIComponent(networkId)}`);
        if (!res.ok) throw new Error('Topology request failed');
        const data = await res.json();
        const n = data.nodes.map((nd: any) => ({ id: String(nd.id), position: { x: nd.x, y: nd.y }, data: { label: nd.label }, style: { width: 140, padding: 8 } }));
        const e = data.edges.map((ed: any) => ({ id: ed.id, source: String(ed.source), target: String(ed.target), animated: false }));
        setNodes(n);
        setEdges(e as Edge[]);
      } catch (err) {
        console.error('Failed to load topology', err);
      }
    };

    void loadTopology();
  }, [networkId]);

  if (nodes.length === 0) {
    return <div style={{ height: 360, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>No topology available</div>;
  }

  return (
    <div style={{ height: 520, borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(125,211,252,0.08)' }}>
      <ReactFlow nodes={nodes} edges={edges} fitView attributionPosition="bottom-left">
        <Background gap={16} />
        <MiniMap nodeColor={(n) => '#7dd3fc'} zoomable pannable />
        <Controls />
      </ReactFlow>
    </div>
  );
}
