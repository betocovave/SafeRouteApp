import React, { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { api } from '../api/client';
import type { Category, Incident, User } from '../api/types';
import { Button, Card, Field, Heading } from '../components/ui';
import type { Palette } from '../theme/colors';

export function AdminScreen({ colors, onBack }: { colors: Palette; onBack: () => void }) {
  const [users, setUsers] = useState<(User & { active: boolean })[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [category, setCategory] = useState<Category | null>(null);
  const [moderating, setModerating] = useState<Incident | null>(null);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  async function load(next = 0) {
    setBusy(true); setError('');
    try {
      const [u, i, c] = await Promise.all([api<(User & { active: boolean })[]>('/admin/users?offset='+next), api<Incident[]>('/admin/incidents?offset='+next), api<Category[]>('/admin/categories')]);
      setUsers(next ? old => [...old, ...u] : u); setIncidents(next ? old => [...old, ...i] : i); setCategories(c); setOffset(next);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, []);
  async function moderate(status: string) {
    if (!moderating) return;
    setBusy(true);
    try { await api('/admin/incidents/'+moderating.id, 'PATCH', { status, reason }); setModerating(null); setReason(''); await load(); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function saveCategory() {
    if (!category) return;
    setBusy(true);
    try { const { id, ...body } = category; await api('/admin/categories/'+id, 'PUT', body); setCategory(null); await load(); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <ScrollView contentContainerStyle={{ padding: 20, gap: 16, paddingBottom: 35 }}><Button colors={colors} secondary label="Volver al perfil" onPress={onBack} /><Heading colors={colors}>Administración</Heading><Text style={{ color: colors.muted }}>Las acciones quedan registradas para auditoría.</Text>
    {!!error && <Text style={{ color: colors.danger }}>{error}</Text>}
    {moderating && <Card colors={colors}><Heading small colors={colors}>Revisar {moderating.category}</Heading><Text style={{ color: colors.text }}>{moderating.description}</Text><Field colors={colors} label="Motivo de la acción" value={reason} onChangeText={setReason} /><Button colors={colors} busy={busy} label="Confirmar incidente" onPress={() => void moderate('confirmed')} /><Button colors={colors} secondary busy={busy} label="Marcar finalizado" onPress={() => void moderate('resolved')} /><Button colors={colors} secondary busy={busy} label="Ocultar contenido" onPress={() => void moderate('hidden')} /><Button colors={colors} secondary label="Cancelar revisión" onPress={() => setModerating(null)} /></Card>}
    {category && <Card colors={colors}><Heading small colors={colors}>Editar categoría</Heading><Field colors={colors} label="Nombre" value={category.name} onChangeText={v => setCategory({ ...category, name: v })} /><Field colors={colors} label="Severidad (0 a 1)" keyboardType="decimal-pad" value={String(category.severity)} onChangeText={v => setCategory({ ...category, severity: Number(v) })} /><Field colors={colors} label="Vigencia en horas (1 a 720)" keyboardType="number-pad" value={String(category.ttl_hours)} onChangeText={v => setCategory({ ...category, ttl_hours: Number(v) })} /><View style={{ gap: 8 }}><Button colors={colors} secondary label={category.critical ? 'Crítico: sí' : 'Crítico: no'} onPress={() => setCategory({ ...category, critical: !category.critical })} /><Button colors={colors} secondary label={category.active ? 'Disponible: sí' : 'Disponible: no'} onPress={() => setCategory({ ...category, active: !category.active })} /></View><Button colors={colors} busy={busy} label="Guardar categoría" onPress={() => void saveCategory()} /><Button colors={colors} secondary label="Cancelar edición" onPress={() => setCategory(null)} /></Card>}
    <Heading small colors={colors}>Usuarios</Heading>{users.map(u => <Card key={u.id} colors={colors}><Text style={{ color: colors.text }}>{u.name} · {u.email}</Text><Button colors={colors} secondary busy={busy} disabled={u.role === 'admin'} label={u.active ? 'Suspender cuenta' : 'Reactivar cuenta'} onPress={() => { setBusy(true); void api('/admin/users/'+u.id, 'PATCH', { active: !u.active }).then(() => load()).catch(e => { setError(e.message); setBusy(false); }); }} /></Card>)}
    <Heading small colors={colors}>Reportes y contenido</Heading>{incidents.map(i => <Card key={i.id} colors={colors}><Text style={{ color: colors.text }}>{i.category} · {i.status}</Text><Text style={{ color: colors.muted }}>{i.description}</Text><Button colors={colors} secondary label="Revisar reporte" onPress={() => setModerating(i)} /></Card>)}
    <Heading small colors={colors}>Categorías</Heading>{categories.map(c => <Card key={c.id} colors={colors}><Text style={{ color: colors.text }}>{c.name}</Text><Button colors={colors} secondary label="Editar categoría" onPress={() => setCategory(c)} /></Card>)}
    <Button colors={colors} busy={busy} secondary label="Cargar más usuarios y reportes" onPress={() => void load(offset+50)} />
  </ScrollView>;
}
