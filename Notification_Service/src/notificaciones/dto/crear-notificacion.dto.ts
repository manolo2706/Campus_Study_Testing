import { IsInt, IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class CrearNotificacionDto {
  @IsInt()
  usuario_id: number;

  @IsString()
  @IsNotEmpty()
  tipo: string;

  @IsString()
  @IsNotEmpty()
  titulo: string;

  @IsString()
  @IsNotEmpty()
  mensaje: string;

  @IsOptional()
  @IsInt()
  referencia_id?: number;
}