import asyncpg
from models.enrollment import PackageCreate, PackageUpdate, PackageOfferingCreate

async def get_all_packages(db: asyncpg.Connection):
    packages = await db.fetch("SELECT * FROM packages ORDER BY name")
    return [dict(p) for p in packages]

async def create_package(data: PackageCreate, db: asyncpg.Connection):
    result = await db.fetchrow(
        """INSERT INTO packages (name, description, base_price)
           VALUES ($1, $2, $3) RETURNING id""",
        data.name, data.description, data.base_price
    )
    package_id = result['id']
    
    # Add courses to package
    if data.course_ids:
        for course_id in data.course_ids:
            await db.execute(
                "INSERT INTO package_courses (package_id, course_id) VALUES ($1, $2)",
                package_id, course_id
            )
    
    return {"id": package_id, "message": "Paquete creado exitosamente"}

async def update_package(package_id: int, data: PackageUpdate, db: asyncpg.Connection):
    fields = []
    values = []
    idx = 1
    
    update_data = data.dict(exclude_unset=True, exclude={'course_ids'})
    for field, value in update_data.items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if fields:
        values.append(package_id)
        query = f"UPDATE packages SET {', '.join(fields)} WHERE id = ${idx}"
        await db.execute(query, *values)
    
    # Update courses if provided
    if data.course_ids is not None:
        await db.execute("DELETE FROM package_courses WHERE package_id = $1", package_id)
        for course_id in data.course_ids:
            await db.execute(
                "INSERT INTO package_courses (package_id, course_id) VALUES ($1, $2)",
                package_id, course_id
            )
    
    return {"message": "Paquete actualizado correctamente"}

async def delete_package(package_id: int, db: asyncpg.Connection):
    await db.execute("DELETE FROM packages WHERE id = $1", package_id)
    return {"message": "Paquete eliminado correctamente"}

async def get_package_offerings(cycle_id: int, db: asyncpg.Connection):
    offerings = await db.fetch(
        """SELECT po.*, p.name as package_name, p.description, p.base_price,
                  cyc.name as cycle_name
           FROM package_offerings po
           JOIN packages p ON po.package_id = p.id
           JOIN cycles cyc ON po.cycle_id = cyc.id
           WHERE po.cycle_id = $1
           ORDER BY p.name, po.group_label""",
        cycle_id
    )
    return [dict(o) for o in offerings]

async def create_package_offering(data: PackageOfferingCreate, db: asyncpg.Connection):
    result = await db.fetchrow(
        """INSERT INTO package_offerings (package_id, cycle_id, group_label, price_override, capacity)
           VALUES ($1, $2, $3, $4, $5) RETURNING id""",
        data.package_id, data.cycle_id, data.group_label, data.price_override, data.capacity
    )
    package_offering_id = result['id']
    
    # Map to specific course offerings if provided
    if data.course_offering_ids:
        for co_id in data.course_offering_ids:
            await db.execute(
                """INSERT INTO package_offering_courses (package_offering_id, course_offering_id)
                   VALUES ($1, $2)""",
                package_offering_id, co_id
            )
    
    return {"id": package_offering_id, "message": "Oferta de paquete creada exitosamente"}
