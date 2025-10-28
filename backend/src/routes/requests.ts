import { Router } from 'express';
import { pool } from '../db/pool';

const router = Router();

type RequestItemInput = {
  partNumber?: string | number;
  name?: string;
  quantity?: number;
  unit?: string;
  brand?: string;
  model?: string;
  serialNumber?: number;
  scheme?: string;
  posScheme?: string;
  material?: string;
  comment?: string;
  unitPrice?: number;
  totalPrice?: number;
  productId?: number;
};

type RequestInput = {
  idRequest?: number;
  typeRequest?: string;
  datetimeComing?: string;
  datetimeDelivery?: string;
  status?: string;
  totalPrice?: number;
  items?: RequestItemInput[];
};

router.get('/', async (_req, res, next) => {
  try {
    const { rows: requestRows } = await pool.query(
      `select
         r.id,
         r.id_request as "idRequest",
         r.type_request as "typeRequest",
         rt.description as "typeDescription",
         r.datetime_coming as "datetimeComing",
         r.datetime_delivery as "datetimeDelivery",
         r.status,
         rs.description as "statusDescription",
         r.total_price as "totalPrice"
       from requests r
       left join request_types rt on rt.code = r.type_request
       left join request_statuses rs on rs.code = r.status
       order by r.datetime_coming desc`
    );

    const { rows: itemRows } = await pool.query(
      `select
         id,
         part_number as "partNumber",
         name,
         quantity,
         unit,
         brand,
         model,
         serial_number as "serialNumber",
         scheme,
         pos_scheme as "posScheme",
         material,
         comment,
         unit_price as "unitPrice",
         total_price as "totalPrice",
         request_id as "requestId",
         product_id as "productId"
       from request_items`
    );

    const itemsByRequest = itemRows.reduce<Record<number, typeof itemRows>>(
      (acc, item) => {
        const key = item.requestId;
        if (!key) {
          return acc;
        }
        acc[key] = acc[key] ? [...acc[key], item] : [item];
        return acc;
      },
      {}
    );

    const payload = requestRows.map((request) => ({
      ...request,
      items: itemsByRequest[request.id] ?? []
    }));

    res.json(payload);
  } catch (error) {
    next(error);
  }
});

router.post('/', async (req, res, next) => {
  const {
    idRequest,
    typeRequest,
    datetimeComing,
    datetimeDelivery,
    status,
    totalPrice,
    items
  }: RequestInput = req.body ?? {};

  if (!idRequest || Number.isNaN(Number(idRequest))) {
    res.status(400).json({ message: 'Field "idRequest" must be a number' });
    return;
  }

  if (!datetimeComing) {
    res
      .status(400)
      .json({ message: 'Field "datetimeComing" must be a valid ISO date string' });
    return;
  }

  const parsedComing = new Date(datetimeComing);
  if (Number.isNaN(parsedComing.valueOf())) {
    res
      .status(400)
      .json({ message: 'Field "datetimeComing" must be a valid ISO date string' });
    return;
  }

  let parsedDelivery: Date | null = null;
  if (datetimeDelivery) {
    const date = new Date(datetimeDelivery);
    if (Number.isNaN(date.valueOf())) {
      res.status(400).json({
        message: 'Field "datetimeDelivery" must be a valid ISO date string'
      });
      return;
    }
    parsedDelivery = date;
  }

  const client = await pool.connect();

  try {
    await client.query('begin');

    const { rows: requestRows } = await client.query(
      `insert into requests (
        id_request,
        type_request,
        datetime_coming,
        datetime_delivery,
        status,
        total_price
      ) values ($1,$2,$3,$4,$5,$6)
      returning
        id,
        id_request as "idRequest",
        type_request as "typeRequest",
        datetime_coming as "datetimeComing",
        datetime_delivery as "datetimeDelivery",
        status,
        total_price as "totalPrice"`,
      [
        idRequest,
        typeRequest ?? null,
        parsedComing.toISOString(),
        parsedDelivery ? parsedDelivery.toISOString() : null,
        status ?? null,
        totalPrice ?? null
      ]
    );

    const createdRequest = requestRows[0];
    const createdItems: unknown[] = [];

    if (Array.isArray(items) && items.length > 0) {
      for (const item of items) {
        if (!item?.name) {
          throw new Error('Each request item must include "name"');
        }

        const itemPartNumber =
          item.partNumber === undefined || item.partNumber === null
            ? null
            : typeof item.partNumber === 'number'
              ? item.partNumber.toString()
              : typeof item.partNumber === 'string'
                ? item.partNumber.trim() || null
                : null;

        const result = await client.query(
          `insert into request_items (
            part_number,
            name,
            quantity,
            unit,
            brand,
            model,
            serial_number,
            scheme,
            pos_scheme,
            material,
            comment,
            unit_price,
            total_price,
            request_id,
            product_id
          ) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
          returning
            id,
            part_number as "partNumber",
            name,
            quantity,
            unit,
            brand,
            model,
            serial_number as "serialNumber",
            scheme,
            pos_scheme as "posScheme",
            material,
            comment,
            unit_price as "unitPrice",
            total_price as "totalPrice",
            request_id as "requestId",
            product_id as "productId"`,
          [
            itemPartNumber,
            item.name,
            item.quantity ?? null,
            item.unit ?? null,
            item.brand ?? null,
            item.model ?? null,
            item.serialNumber ?? null,
            item.scheme ?? null,
            item.posScheme ?? null,
            item.material ?? null,
            item.comment ?? null,
            item.unitPrice ?? null,
            item.totalPrice ?? null,
            createdRequest.id,
            item.productId ?? null
          ]
        );

        createdItems.push(result.rows[0]);
      }
    }

    await client.query('commit');

    res.status(201).json({
      ...createdRequest,
      items: createdItems
    });
  } catch (error) {
    await client.query('rollback');
    next(error);
  } finally {
    client.release();
  }
});

export default router;
