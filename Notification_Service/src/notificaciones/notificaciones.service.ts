import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';

import type { Model, Types } from 'mongoose';
import { CrearNotificacionDto } from './dto/crear-notificacion.dto.js';
import { Notificacion } from './schemas/notificacion.schema.js';
@Injectable()
export class NotificacionesService {
  constructor(
    @InjectModel(Notificacion.name)
    private readonly notificacionModel: Model<Notificacion>,
  ) {}

  async crear(dto: CrearNotificacionDto) {
    const notificacion = await this.notificacionModel.create(dto);
    return { id: notificacion.id };
  }

  async listarPorUsuario(usuarioId: number) {
    const notificaciones = await this.notificacionModel
      .find({ usuario_id: usuarioId })
      .sort({ fecha_creacion: -1 })
      .limit(50)
      .lean();

    return notificaciones.map(({ _id, usuario_id, ...resto }) => ({ id: _id.toString(), ...resto }));
  }

  async marcarLeida(id: Types.ObjectId, usuarioId: number) {
    const resultado = await this.notificacionModel.updateOne(
      { _id: id, usuario_id: usuarioId },
      { leida: true },
    );

    if (resultado.matchedCount === 0) throw new NotFoundException(`No existe la notificación ${id}`);
  }
}