import { useState, useCallback, useEffect } from 'react';

const API_BASE = '';
const SKILLS_ENDPOINT = `${API_BASE}/api/skills`;

export default function useSkills() {
  const [skills, setSkills] = useState([]);
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch available skills on mount
  useEffect(() => {
    fetch(SKILLS_ENDPOINT)
      .then(res => res.json())
      .then(data => {
        const list = data.skills || [];
        setSkills(list);
        // Default: select all skills
        setSelectedSkills(list.map(s => s.dir_name));
      })
      .catch(() => {
        // Fallback: no skills available
        setSkills([]);
        setSelectedSkills([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const toggleSkill = useCallback((dirName) => {
    setSelectedSkills(prev =>
      prev.includes(dirName)
        ? prev.filter(d => d !== dirName)
        : [...prev, dirName]
    );
  }, []);

  const selectAll = useCallback(() => {
    setSelectedSkills(skills.map(s => s.dir_name));
  }, [skills]);

  const deselectAll = useCallback(() => {
    setSelectedSkills([]);
  }, []);

  return {
    skills,
    selectedSkills,
    loading,
    toggleSkill,
    selectAll,
    deselectAll,
  };
}
