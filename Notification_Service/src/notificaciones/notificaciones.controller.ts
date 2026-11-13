import { Body, Controller, Get, HttpCode, HttpStatus, Param, Patch, Post, UseGuards } from '@nestjs/common';
import { ParseObjectIdPipe } from '@nestjs/mongoose';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { Types } from 'mongoose';

import { UsuarioId } from '../common/decorators/usuario-id.decorator.js';
import { JwtGuard } from '../common/guards/jwt.guard.js';
import { CrearNotificacionDto } from './dto/crear-notificacion.dto.js';
import { NotificacionesService } from './notificaciones.service.js';

@ApiTags('Notificaciones')
@Controller('notificaciones')
export class NotificacionesController {
  constructor(private readonly notificacionesService: NotificacionesService) {}

  @Post()
  crear(@Body() dto: CrearNotificacionDto) {
    return this.notificacionesService.crear(dto);
  }

  @Get('me')
  @ApiBearerAuth()
  @UseGuards(JwtGuard)
  listarMias(@UsuarioId() usuarioId: number) {
    return this.notificacionesService.listarPorUsuario(usuarioId);
  }

  @Patch(':id/leida')
  @ApiBearerAuth()
  @UseGuards(JwtGuard)
  @HttpCode(HttpStatus.NO_CONTENT)
  marcarLeida(@Param('id', ParseObjectIdPipe) id: Types.ObjectId, @UsuarioId() usuarioId: number) {
    return this.notificacionesService.marcarLeida(id, usuarioId);
  }
}