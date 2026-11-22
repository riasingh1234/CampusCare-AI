import { useEffect, useState } from 'react';

// Simulates API latency so loading states can be designed now. Remove when real API calls land.
export default function useLoading(ms = 450) {
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setLoading(false), ms);
    return () => clearTimeout(t);
  }, [ms]);
  return loading;
}
