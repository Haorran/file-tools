const BASE = '/app/file-tools/api';

export async function checkTaskStatus(taskId) {
  try {
    const res = await fetch(`${BASE}/task-status?taskId=${taskId}`);
    if (!res.ok) return 'unknown';
    const data = await res.json();
    return data.status; // 'running' | 'done'
  } catch {
    return 'unknown';
  }
}

export async function listTasks() {
  try {
    const res = await fetch(`${BASE}/tasks`);
    if (!res.ok) return { tasks: [] };
    return res.json();
  } catch {
    return { tasks: [] };
  }
}

export async function startCompare({ mode, dirA, dirB, blockSize }) {
  const body = { mode, dirA, dirB };
  if (blockSize !== undefined) body.blockSize = blockSize;
  let res;
  try {
    res = await fetch(`${BASE}/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new Error(`网络错误: ${e.message}`);
  }
  if (!res.ok) {
    let err;
    try { err = await res.json(); } catch { err = {}; }
    throw new Error(err.error || `服务端返回 ${res.status}`);
  }
  return res.json();
}

export async function startDuplicate({ mode, scanDir, filterKB, blockSize }) {
  const body = { mode, scanDir };
  if (filterKB !== undefined && filterKB !== '') body.filterKB = Number(filterKB);
  if (blockSize !== undefined) body.blockSize = blockSize;
  let res;
  try {
    res = await fetch(`${BASE}/duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new Error(`网络错误: ${e.message}`);
  }
  if (!res.ok) {
    let err;
    try { err = await res.json(); } catch { err = {}; }
    throw new Error(err.error || `服务端返回 ${res.status}`);
  }
  return res.json();
}

export async function stopTask(taskId) {
  try {
    const res = await fetch(`${BASE}/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ taskId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `服务端返回 ${res.status}`);
    return data;
  } catch (e) {
    throw new Error(`终止失败: ${e.message}`);
  }
}

export async function listLogs() {
  try {
    const res = await fetch(`${BASE}/logs`);
    if (!res.ok) return { logs: [] };
    return res.json();
  } catch {
    return { logs: [] };
  }
}

export async function getLog(tool, filename) {
  try {
    const res = await fetch(`${BASE}/logs/${tool}/${filename}`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function deleteLog(tool, filename) {
  try {
    const res = await fetch(`${BASE}/logs/${tool}/${filename}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `服务端返回 ${res.status}`);
    return data;
  } catch (e) {
    throw new Error(`删除失败: ${e.message}`);
  }
}
