import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import type { Request } from 'express';

@Injectable()
export class JwtGuard implements CanActivate {
  constructor(private readonly jwtService: JwtService) {}

  async canActivate(context: ExecutionContext) {
    const request = context.switchToHttp().getRequest<Request & { usuarioId: number }>();
    const [tipo, token] = request.headers.authorization?.split(' ') ?? [];

    if (tipo !== 'Bearer' || !token) throw new UnauthorizedException('Falta el token');

    try {
      const payload = await this.jwtService.verifyAsync(token, { algorithms: ['HS256'] });
      request.usuarioId = Number(payload.sub);
    } catch {
      throw new UnauthorizedException('Token inválido o expirado');
    }

    return true;
  }
}