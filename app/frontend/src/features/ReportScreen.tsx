import React, { useState } from 'react';
import { Alert, Image, ScrollView, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as Crypto from 'expo-crypto';
import type { Category, Point } from '../api/types';
import { Button, Card, Field, Heading } from '../components/ui';
import { enqueue, keepPhoto, syncReports } from '../storage/local';
import type { Palette } from '../theme/colors';

export function ReportScreen({ colors, point, categories, online, onDone }: { colors: Palette; point: Point | null; categories: Category[]; online: boolean; onDone: () => void }) {
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [photo, setPhoto] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function pick(camera: boolean) {
    try {
      const permission = camera ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) { setError('Permiso de cámara o fotografías denegado. Puedes reportar sin foto.'); return; }
      const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.75, exif: false };
      const result = camera ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
      if (!result.canceled) setPhoto(result.assets[0].uri);
    } catch (e) { setError((e as Error).message); }
  }
  async function submit() {
    if (!point || !category || description.trim().length < 5) { setError('Selecciona una categoría, una ubicación y una descripción de al menos 5 caracteres.'); return; }
    setBusy(true); setError('');
    try {
      const client_id = Crypto.randomUUID();
      const local_photo = photo ? await keepPhoto(photo, client_id) : undefined;
      await enqueue({ ...point, category_id: category, description: description.trim(), client_id, occurred_at: new Date().toISOString(), local_photo });
      if (online) {
        const remaining = await syncReports();
        const item = remaining.find(i => i.client_id === client_id);
        Alert.alert(item ? 'Envío pendiente' : 'Reporte enviado', item ? item.error || 'Se reintentará al recuperar conexión.' : 'Tu reporte ya está registrado.');
      } else Alert.alert('Reporte guardado', 'Se enviará cuando vuelva la conexión. Aún no es visible para otros usuarios.');
      onDone();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 20, gap: 17, paddingBottom: 35 }}><Heading colors={colors}>Reportar incidente</Heading><Text style={{ color: colors.muted }}>Comparte lo que observas. Adjunta evidencia solo si puedes hacerlo con seguridad.</Text>
    <Card colors={colors}><Text style={{ color: colors.text, fontWeight: '700' }}>Ubicación del reporte</Text><Text style={{ color: colors.muted }}>{point ? `${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)}` : 'Activa tu ubicación o selecciona un punto en el mapa.'}</Text><Text style={{ color: colors.muted, fontSize: 12 }}>Para cambiarla, vuelve al mapa y toca el lugar del incidente.</Text></Card>
    <Text style={{ color: colors.text, fontWeight: '700' }}>¿Qué está ocurriendo?</Text><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{categories.map(c => <Button key={c.id} colors={colors} secondary={category !== c.id} label={c.name} onPress={() => setCategory(c.id)} />)}</View>
    {!categories.length && <Text style={{ color: colors.danger }}>Conecta la app al servidor para cargar las categorías iniciales.</Text>}
    <Field colors={colors} label="Descripción" multiline numberOfLines={4} maxLength={1000} value={description} onChangeText={setDescription} placeholder="Describe la situación sin publicar datos personales." />
    {!!photo && <Image source={{ uri: photo }} style={{ height: 180, borderRadius: 18 }} />}
    <View style={{ flexDirection: 'row', gap: 8 }}><Button colors={colors} secondary label="Elegir foto" icon="image-outline" onPress={() => void pick(false)} /><Button colors={colors} secondary label="Cámara" icon="camera-outline" onPress={() => void pick(true)} /></View>
    {!!photo && <Button colors={colors} secondary label="Quitar fotografía" onPress={() => setPhoto('')} />}
    {!!error && <Text style={{ color: colors.danger }}>{error}</Text>}
    <Button colors={colors} busy={busy} disabled={!point} label={online ? 'Enviar reporte' : 'Guardar para enviar'} onPress={() => void submit()} />
    <Button colors={colors} secondary label="Volver al mapa" onPress={onDone} />
  </ScrollView>;
}
