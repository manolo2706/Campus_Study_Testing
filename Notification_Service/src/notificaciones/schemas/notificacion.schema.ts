import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import type { HydratedDocument } from 'mongoose';

export type NotificacionDocument = HydratedDocument<Notificacion>;

@Schema({
  collection: 'notificaciones',
  timestamps: { createdAt: 'fecha_creacion', updatedAt: false },
  versionKey: false,
})
export class Notificacion {
  @Prop({ required: true })
  usuario_id: number;

  @Prop({ required: true })
  tipo: string;

  @Prop({ required: true })
  titulo: string;

  @Prop({ required: true })
  mensaje: string;

  @Prop({ default: false })
  leida: boolean;

  @Prop()
  referencia_id?: number;

  fecha_creacion: Date;
}

export const NotificacionSchema = SchemaFactory.createForClass(Notificacion);

NotificacionSchema.index({ usuario_id: 1, fecha_creacion: -1 });