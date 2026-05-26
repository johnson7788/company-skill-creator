import React from 'react';

export default function SkillPanel({ skills, selectedSkills, loading, onToggle, onSelectAll, onDeselectAll }) {
  const allSelected = skills.length > 0 && selectedSkills.length === skills.length;
  const noneSelected = selectedSkills.length === 0;

  if (loading) {
    return (
      <aside className="skill-panel">
        <div className="skill-panel-header">
          <h3>Skills</h3>
        </div>
        <div className="skill-panel-loading">Loading...</div>
      </aside>
    );
  }

  return (
    <aside className="skill-panel">
      <div className="skill-panel-header">
        <h3>Skills ({selectedSkills.length}/{skills.length})</h3>
        <div className="skill-panel-actions">
          <button
            className="btn-skill-action"
            onClick={onSelectAll}
            disabled={allSelected}
            title="全选"
          >
            全选
          </button>
          <button
            className="btn-skill-action"
            onClick={onDeselectAll}
            disabled={noneSelected}
            title="取消全选"
          >
            清空
          </button>
        </div>
      </div>
      <div className="skill-list">
        {skills.length === 0 ? (
          <div className="skill-empty">No skills found</div>
        ) : (
          skills.map(skill => (
            <label
              key={skill.dir_name}
              className={`skill-item ${selectedSkills.includes(skill.dir_name) ? 'selected' : ''}`}
            >
              <input
                type="checkbox"
                checked={selectedSkills.includes(skill.dir_name)}
                onChange={() => onToggle(skill.dir_name)}
              />
              <div className="skill-info">
                <span className="skill-name">{skill.name}</span>
                {skill.description && (
                  <span className="skill-description">{skill.description}</span>
                )}
              </div>
            </label>
          ))
        )}
      </div>
    </aside>
  );
}
